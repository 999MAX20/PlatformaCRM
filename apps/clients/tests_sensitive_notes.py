import json
import csv
import io

from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.activities.models import Segment, SegmentFilter
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission
from apps.clients.models import Client
from apps.clients.serializers import ClientSerializer
from apps.leads.models import Lead
from apps.core.export_jobs import process_export_job
from apps.core.import_export import export_clients
from apps.core.models import ExportJob
from apps.integrations.models import ApiToken


class ClientSensitiveNotesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="notes-owner", email="notes-owner@example.test")
        cls.operator = User.objects.create_user(username="notes-operator", email="notes-operator@example.test")
        cls.manager = User.objects.create_user(username="notes-manager", email="notes-manager@example.test")
        cls.business = Business.objects.create(owner=cls.owner, name="Notes", slug="notes-access")
        for user, role in ((cls.owner, "owner"), (cls.operator, "operator"), (cls.manager, "manager")):
            custom = BusinessRole.objects.create(business=cls.business, name=f"Custom {role}")
            for resource in ("clients", "leads"):
                for action in ("view", "create", "update"):
                    RolePermission.objects.create(business_role=custom, resource=resource, action=action, scope="business")
            BusinessMember.objects.create(business=cls.business, user=user, role=role, business_role=custom)
        cls.secret = "AUD03 confidential client note"
        cls.customer = Client.objects.create(business=cls.business, full_name="Visible customer", notes=cls.secret)
        cls.lead = Lead.objects.create(business=cls.business, client=cls.customer, responsible_user=cls.operator)
        cls.segment = Segment.objects.create(business=cls.business, name="Everyone")

    def setUp(self):
        self.api = APIClient()

    def test_role_policy_is_identical_for_list_detail_nested_cards_and_segments(self):
        paths = ["/api/clients/", f"/api/clients/{self.customer.pk}/",
                 f"/api/clients/{self.customer.pk}/crm-card/", f"/api/leads/{self.lead.pk}/crm-card/",
                 f"/api/segments/{self.segment.pk}/evaluate/"]
        for actor, allowed in ((self.owner, True), (self.manager, True), (self.operator, False)):
            self.api.force_authenticate(actor)
            for path in paths:
                with self.subTest(actor=actor.username, path=path):
                    response = self.api.get(path)
                    self.assertEqual(response.status_code, 200, response.data)
                    self.assertEqual(self.secret in json.dumps(response.data), allowed)
                    self.assertIn("Visible customer", json.dumps(response.data))

    def test_masked_edit_preserves_notes_and_returns_no_private_value(self):
        self.api.force_authenticate(self.operator)
        response = self.api.patch(f"/api/clients/{self.customer.pk}/", {"full_name": "Edited customer", "notes": ""}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["notes"], "")
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.notes, self.secret)
        self.assertEqual(self.customer.full_name, "Edited customer")
        response = self.api.patch(f"/api/clients/{self.customer.pk}/", {"notes": "Overwrite"}, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.api.force_authenticate(self.owner)
        response = self.api.patch(f"/api/clients/{self.customer.pk}/", {"notes": ""}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.notes, "")

    def test_create_response_obeys_policy_and_regular_operator_creation_works(self):
        self.api.force_authenticate(self.owner)
        response = self.api.post("/api/clients/", {"business": self.business.pk, "full_name": "Created", "notes": self.secret}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["notes"], self.secret)
        self.api.force_authenticate(self.operator)
        response = self.api.post("/api/clients/", {"business": self.business.pk, "full_name": "Operator client", "notes": ""}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["notes"], "")

    def test_no_actor_fails_closed_and_mixed_business_cache_is_separate(self):
        self.assertEqual(ClientSerializer(self.customer).data["notes"], "")
        other = Business.objects.create(owner=self.operator, name="Other", slug="notes-other")
        own = Client.objects.create(business=other, full_name="Owned", notes="Own secret")
        rows = ClientSerializer([self.customer, own], many=True, context={"actor": self.operator}).data
        self.assertEqual([row["notes"] for row in rows], ["", "Own secret"])
        self.api.force_authenticate(self.owner)
        self.assertEqual(self.api.get(f"/api/clients/{own.pk}/").status_code, 404)

    def test_list_checks_field_policy_once_per_business(self):
        Client.objects.bulk_create([Client(business=self.business, full_name=f"Client {index}", notes=self.secret) for index in range(20)])
        with CaptureQueriesContext(connection) as queries:
            data = ClientSerializer(Client.objects.filter(business=self.business), many=True, context={"actor": self.operator}).data
        self.assertNotIn(self.secret, json.dumps(data))
        self.assertLessEqual(len(queries), 4)

    def test_sync_csv_matches_notes_policy_and_retains_header_and_contacts(self):
        for actor, allowed in ((self.owner, True), (self.manager, True), (self.operator, False)):
            self.api.force_authenticate(actor)
            response = self.api.get("/api/export/clients/", {"business": self.business.pk})
            self.assertEqual(response.status_code, 200)
            rows = list(csv.DictReader(io.StringIO(response.content.decode())))
            self.assertEqual(rows[0]["notes"], self.secret if allowed else "")
            self.assertEqual(rows[0]["full_name"], self.customer.full_name)
        self.assertNotIn(self.secret, export_clients(self.business).content.decode())

    @override_settings(EXPORT_SYNC_MAX_ROWS=0, CELERY_TASK_ALWAYS_EAGER=False)
    def test_queued_csv_and_download_recheck_role_without_rewriting_file(self):
        # Include quoted commas/newlines so redaction cannot split records by line.
        secret = 'private, "quoted"\nsecond line'
        self.customer.notes = secret
        self.customer.save()
        self.api.force_authenticate(self.manager)
        response = self.api.get("/api/export/clients/", {"business": self.business.pk})
        self.assertEqual(response.status_code, 202, response.data)
        job = process_export_job(response.data["id"])
        self.assertEqual(job.status, ExportJob.Statuses.SUCCEEDED, job.error)
        with job.result_file.open("rb") as stored:
            original = stored.read()
        self.assertEqual(list(csv.DictReader(io.StringIO(original.decode())))[0]["notes"], secret)
        path = f"/api/export-jobs/{job.pk}/download/"
        download = self.api.get(path)
        self.assertEqual(download.status_code, 200)
        self.assertEqual(b"".join(download.streaming_content), original)
        BusinessMember.objects.filter(business=self.business, user=self.manager).update(role="operator")
        download = self.api.get(path)
        self.assertEqual(download.status_code, 200)
        rows = list(csv.DictReader(io.StringIO(b"".join(download.streaming_content).decode())))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["notes"], "")
        self.assertEqual(rows[0]["full_name"], self.customer.full_name)
        with job.result_file.open("rb") as stored:
            self.assertEqual(stored.read(), original)
        # The background producer also uses current rights, not creation-time rights.
        response = self.api.get("/api/export/clients/", {"business": self.business.pk})
        job = process_export_job(response.data["id"])
        self.assertEqual(job.status, ExportJob.Statuses.SUCCEEDED, job.error)
        with job.result_file.open("rb") as stored:
            rows = list(csv.DictReader(io.StringIO(stored.read().decode())))
        self.assertEqual(rows[0]["notes"], "")
        BusinessMember.objects.filter(business=self.business, user=self.manager).update(is_active=False)
        self.assertEqual(self.api.get(path).status_code, 404)

    def test_public_token_does_not_inherit_creator_sensitive_field_access(self):
        token = ApiToken(business=self.business, name="Reader", scopes_json=["clients:read"], created_by=self.owner)
        raw = ApiToken.generate_raw_token()
        token.set_raw_token(raw)
        token.save()
        response = self.api.get("/api/public-api/clients/", HTTP_X_ZANI_API_KEY=raw)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data[0]["notes"], "")
        self.assertEqual(response.data[0]["full_name"], self.customer.full_name)

    def test_segment_predicates_cannot_be_used_to_guess_hidden_notes(self):
        private = Segment.objects.create(business=self.business, name="Private selection", cached_count=1)
        condition = SegmentFilter.objects.create(business=self.business, segment=private,
            field="notes", operator="contains", value_json={"value": self.secret})
        self.api.force_authenticate(self.operator)
        for endpoint in (f"/api/segments/{private.pk}/", f"/api/segments/{private.pk}/evaluate/",
                         f"/api/segment-filters/{condition.pk}/"):
            self.assertEqual(self.api.get(endpoint).status_code, 404)
        self.assertEqual(self.api.post(f"/api/segments/{private.pk}/refresh-count/").status_code, 404)
        response = self.api.get("/api/segments/")
        self.assertNotIn("Private selection", json.dumps(response.data))
        self.assertNotIn(self.secret, json.dumps(self.api.get("/api/segment-filters/").data))
        response = self.api.get("/api/clients/", {"segment": private.pk})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["results"], [])
        response = self.api.post("/api/segment-filters/", {"business": self.business.pk,
            "segment": self.segment.pk, "field": "notes", "operator": "contains", "value_json": {"value": "guess"}}, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.api.force_authenticate(self.owner)
        response = self.api.get(f"/api/segments/{private.pk}/evaluate/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)

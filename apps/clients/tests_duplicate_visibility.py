"""Synthetic read-boundary controls; no external services or real contacts."""
import copy
import json
from types import SimpleNamespace
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.activities.models import ActivityEvent
from apps.activities.serializers import ActivityEventSerializer
from apps.bots.models import Bot, BotConversation
from apps.businesses.models import Business, BusinessCapability, BusinessMember, BusinessRole, RolePermission
from apps.clients.models import Client
from apps.clients.duplicate_visibility import project_duplicate_rows
from apps.clients.serializers import DuplicateCheckSerializer
from apps.clients.services import duplicate_payload, find_duplicate_clients
from apps.core.import_export import build_import_preview, confirm_import
from apps.core.models import ImportJob
from apps.core.serializers import ImportJobSerializer
from apps.leads.models import Lead, LeadForm, LeadFormSubmission
from apps.leads.serializers import LeadFormSubmissionSerializer


class DuplicateVisibilityTests(TestCase):
    def setUp(self):
        scanner = patch("apps.core.antivirus.scan_stream", return_value=SimpleNamespace(clean=True))
        scanner.start()
        self.addCleanup(scanner.stop)
        self.owner = User.objects.create_user(username="duplicate-visibility-owner", email="duplicate-owner@example.invalid")
        self.actor = User.objects.create_user(username="duplicate-visibility-creator", email="duplicate-creator@example.invalid", role="business_operator")
        self.business = Business.objects.create(owner=self.owner, name="Duplicate A", slug="duplicate-visibility-a")
        self.other = Business.objects.create(owner=self.owner, name="Duplicate B", slug="duplicate-visibility-b")
        self.role = BusinessRole.objects.create(business=self.business, name="Create without read")
        BusinessMember.objects.create(business=self.business, user=self.actor, role="operator", business_role=self.role)
        RolePermission.objects.create(business_role=self.role, resource="clients", action="create", scope="business")
        self.read_permission = RolePermission.objects.create(business_role=self.role, resource="clients", action="view", scope="none", is_allowed=False)
        for action in ["view", "update"]:
            RolePermission.objects.create(business_role=self.role, resource="conversations", action=action, scope="business")
        self.name = "PRIVATE_DUPLICATE_907"
        self.phone = "+77015550907"
        self.email = "private907@example.invalid"
        self.customer = Client.objects.create(business=self.business, full_name=self.name, phone=self.phone, email=self.email,
                                              whatsapp_id="private-wa-907", telegram_id="private-tg-907", instagram_id="private-ig-907")
        self.request = SimpleNamespace(user=self.actor, META={})
        self.api = APIClient()
        self.api.force_authenticate(self.actor)

    def grant(self, allowed=True, scope="business"):
        self.read_permission.is_allowed = allowed
        self.read_permission.scope = scope
        self.read_permission.save()

    def check(self, **identity):
        return self.api.post("/api/clients/check-duplicates/", {"business": self.business.pk, **identity}, format="json")

    def assert_restricted(self, rows):
        self.assertTrue(rows, "Existing duplicate warning must remain")
        for row in rows:
            self.assertIsNone(row["id"])
            for field in ["full_name", "phone", "email"]:
                self.assertFalse(row.get(field))
        self.assertNotIn(self.name, json.dumps(rows))
        self.assertNotIn(self.email, json.dumps(rows))

    def job(self, duplicates=None):
        return ImportJob.objects.create(business=self.business, actor=self.actor, entity_type="clients", status="previewed",
            source_file=SimpleUploadedFile("synthetic.csv", b"full_name,phone\nUploaded person,+77015550907\n", content_type="text/csv"),
            duplicates_json={"rows": [{"row": 1, "payload": {"full_name": "Uploaded person", "phone": self.phone},
                "duplicates": duplicate_payload([self.customer]) if duplicates is None else duplicates}]})

    def test_create_only_check_retains_warning_without_contact_details(self):
        response = self.check(phone="8 (701) 555-09-07")
        self.assertEqual(response.status_code, 200, response.data)
        self.assert_restricted(response.data["duplicates"])

    def test_all_identity_aliases_use_same_read_guard(self):
        for field, value in [("phone", self.phone), ("email", self.email.upper()), ("whatsapp_id", self.customer.whatsapp_id),
                             ("telegram_id", self.customer.telegram_id), ("instagram_id", self.customer.instagram_id)]:
            with self.subTest(field=field):
                response = self.check(**{field: value})
                self.assertEqual(response.status_code, 200)
                self.assert_restricted(response.data["duplicates"])

    def test_explicit_view_and_owner_keep_ordinary_duplicate_details(self):
        self.grant()
        response = self.check(phone=self.phone)
        self.assertEqual(response.data["duplicates"][0]["id"], self.customer.pk)
        self.assertEqual(response.data["duplicates"][0]["email"], self.email)
        self.api.force_authenticate(self.owner)
        response = self.check(email=self.email)
        self.assertEqual(response.data["duplicates"][0]["full_name"], self.name)

    def test_no_view_scope_and_own_team_use_existing_client_policy(self):
        for scope in ["none", "own", "team"]:
            self.grant(True, scope)
            with self.subTest(scope=scope):
                self.assert_restricted(self.check(phone=self.phone).data["duplicates"])

    def test_exclude_hidden_id_cannot_remove_duplicate_warning(self):
        response = self.check(phone=self.phone, exclude_client_id=self.customer.pk)
        self.assert_restricted(response.data["duplicates"])
        self.grant()
        self.assertEqual(self.check(phone=self.phone, exclude_client_id=self.customer.pk).data["duplicates"], [])

    def test_archive_other_business_and_no_match_are_unchanged(self):
        Client.objects.create(business=self.other, full_name="Other private", phone=self.phone)
        self.customer.is_archived = True
        self.customer.save(update_fields=["is_archived"])
        self.assertEqual(self.check(phone=self.phone).data["duplicates"], [])
        self.assertEqual(self.check(phone="+77010000000").data["duplicates"], [])
        self.assertEqual(self.check(business=self.other.pk, phone=self.phone).status_code, 400)

    def test_create_denial_still_denies_check(self):
        self.role.permissions.filter(resource="clients", action="create").update(is_allowed=False)
        self.assertEqual(self.check(phone=self.phone).status_code, 403)

    def test_import_create_response_masks_existing_db_contact_but_keeps_upload(self):
        upload = SimpleUploadedFile("synthetic.csv", b"full_name,phone\nUploaded person,+77015550907\n", content_type="text/csv")
        response = self.api.post("/api/import-jobs/", {"business": self.business.pk, "entity_type": "clients", "source_file": upload}, format="multipart")
        self.assertEqual(response.status_code, 201, response.data)
        row = response.data["duplicates_json"]["rows"][0]
        self.assert_restricted(row["duplicates"])
        self.assertEqual(row["payload"]["full_name"], "Uploaded person")
        self.assertEqual(response.data["summary_json"]["duplicates"], 1)

    def test_saved_preview_rechecks_current_reader_not_job_actor(self):
        self.grant()
        job = self.job()
        allowed = ImportJobSerializer(job, context={"actor": self.owner}).data
        self.assertEqual(allowed["duplicates_json"]["rows"][0]["duplicates"][0]["id"], self.customer.pk)
        self.grant(False, "none")
        hidden = ImportJobSerializer(job, context={"request": self.request}).data
        self.assert_restricted(hidden["duplicates_json"]["rows"][0]["duplicates"])
        job.refresh_from_db()
        self.assertEqual(job.duplicates_json["rows"][0]["duplicates"][0]["full_name"], self.name)

    def test_preview_without_actor_fails_closed(self):
        self.assert_restricted(ImportJobSerializer(self.job()).data["duplicates_json"]["rows"][0]["duplicates"])

    def test_foreign_missing_and_archived_snapshot_follow_current_read_policy(self):
        self.grant()
        foreign = Client.objects.create(business=self.other, full_name=self.name, email=self.email)
        for rows in [duplicate_payload([foreign]), [{"id": 9999999, "full_name": self.name, "phone": self.phone, "email": self.email}]]:
            with self.subTest(rows=rows):
                data = ImportJobSerializer(self.job(rows), context={"actor": self.owner}).data
                self.assert_restricted(data["duplicates_json"]["rows"][0]["duplicates"])
        job = self.job()
        self.customer.is_archived = True
        self.customer.save(update_fields=["is_archived"])
        data = ImportJobSerializer(job, context={"actor": self.owner}).data
        self.assertEqual(data["duplicates_json"]["rows"][0]["duplicates"][0]["id"], self.customer.pk)

    def test_file_local_duplicates_and_original_snapshot_remain_intact(self):
        local = [{"id": "", "full_name": "Duplicate row 1", "matched_fields": ["file_row"]}]
        job = self.job(local)
        original = copy.deepcopy(job.duplicates_json)
        data = ImportJobSerializer(job).data
        self.assertEqual(data["duplicates_json"], original)
        self.assertEqual(job.duplicates_json, original)

    def test_import_confirmation_still_matches_existing_client(self):
        job = self.job()
        job = build_import_preview(job, request=self.request)
        result = confirm_import(job, self.request)
        self.assertEqual(Client.objects.filter(business=self.business, normalized_phone=self.customer.normalized_phone).count(), 1)
        self.assertEqual(result.preview_json["import_summary"]["created"], 0)

    def test_inbox_duplicate_keeps_confirmation_without_hidden_pii(self):
        bot = Bot.objects.create(business=self.business, name="Synthetic inbox")
        conversation = BotConversation.objects.create(bot=bot, business=self.business, channel="website", external_user_id="visitor-907")
        response = self.api.post(f"/api/inbox/conversations/{conversation.pk}/create-client/", {"phone": self.phone}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["requires_confirmation"])
        self.assertFalse(response.data["created"])
        self.assert_restricted(response.data["duplicates"])
        self.assertEqual(Client.objects.filter(business=self.business).count(), 1)

    def test_next_duplicate_check_respects_view_revocation(self):
        self.grant()
        self.assertEqual(self.check(phone=self.phone).data["duplicates"][0]["id"], self.customer.pk)
        self.grant(False, "none")
        self.assert_restricted(self.check(phone=self.phone).data["duplicates"])

    def test_disabled_client_capability_hides_direct_preview_even_for_owner(self):
        job = self.job()
        BusinessCapability.objects.update_or_create(business=self.business, module_key="clients", defaults={"is_enabled": False})
        data = ImportJobSerializer(job, context={"actor": self.owner}).data
        self.assert_restricted(data["duplicates_json"]["rows"][0]["duplicates"])

    def test_form_submission_duplicate_snapshot_does_not_bypass_read_guard(self):
        form = LeadForm.objects.create(business=self.business, name="Synthetic form", title="Synthetic form")
        lead = Lead.objects.create(business=self.business, client=self.customer, responsible_user=self.actor)
        submission = LeadFormSubmission.objects.create(business=self.business, form=form, client=self.customer, lead=lead,
            payload_json={"full_name": "Entered person", "phone": self.phone}, duplicate_json={"duplicates": duplicate_payload([self.customer])})
        data = LeadFormSubmissionSerializer(submission, context={"actor": self.actor}).data
        self.assert_restricted(data["duplicate_json"]["duplicates"])
        self.assertIsNone(data["client"])
        self.assertEqual(data["payload_json"]["full_name"], "Entered person")
        allowed = LeadFormSubmissionSerializer(submission, context={"actor": self.owner}).data
        self.assertEqual(allowed["duplicate_json"]["duplicates"][0]["id"], self.customer.pk)

    def test_form_activity_duplicate_copy_has_no_hidden_client_id(self):
        event = ActivityEvent.objects.create(business=self.business, client=self.customer, event_type="form_submitted",
            metadata={"duplicates": duplicate_payload([self.customer]), "utm": {"source": "synthetic"}})
        data = ActivityEventSerializer(event, context={"actor": self.actor}).data
        rows = data["metadata"]["duplicates"]
        self.assertTrue(rows)
        self.assertTrue(all(row.get("id") is None for row in rows))
        self.assertNotIn(self.name, json.dumps(data))
        self.assertEqual(data["metadata"]["utm"]["source"], "synthetic")
        allowed = ActivityEventSerializer(event, context={"actor": self.owner}).data
        self.assertEqual(allowed["metadata"]["duplicates"][0]["full_name"], self.name)

    def test_restricted_group_is_one_marker_and_does_not_mutate_source(self):
        rows = duplicate_payload([self.customer, self.customer])
        original = copy.deepcopy(rows)
        projected = project_duplicate_rows(rows, actor=self.actor, business=self.business)
        self.assertEqual(len(projected), 1)
        self.assert_restricted(projected)
        self.assertEqual(rows, original)

    def test_malformed_snapshot_ids_and_forged_file_marker_fail_closed(self):
        rows = [{"id": True, "full_name": self.name}, {"id": 10**100, "full_name": self.name},
                {"id": "", "full_name": self.name, "phone": self.phone, "matched_fields": ["file_row"]}]
        projected = project_duplicate_rows(rows, actor=self.owner, business=self.business)
        self.assert_restricted(projected)
        self.assertEqual(len(projected), 1)

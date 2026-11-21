"""OFFICIAL-17: Client import mutations use current per-operation authority."""
import csv
import io
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.access import Actions, Resources, can
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission, Team, TeamMember
from apps.clients.models import Client
from apps.core.import_export import fill_missing_client_fields, import_client_row, import_lead_row, import_deal_row
from apps.core.models import ImportJob
from apps.crm.models import Deal
from apps.integrations.models import BusinessEvent, ConnectorSyncRun
from apps.leads.models import Lead


class ClientImportPermissionTests(TestCase):
    def setUp(self):
        media = tempfile.TemporaryDirectory()
        self.addCleanup(media.cleanup)
        config = override_settings(MEDIA_ROOT=media.name)
        config.enable()
        self.addCleanup(config.disable)
        scanner = patch("apps.core.antivirus.scan_stream", return_value=SimpleNamespace(clean=True))
        scanner.start()
        self.addCleanup(scanner.stop)
        self.owner = User.objects.create_user(username="import-policy-owner", email="import-policy-owner@example.test")
        self.actor = User.objects.create_user(username="import-policy-reader", email="import-policy-reader@example.test")
        self.peer = User.objects.create_user(username="import-policy-peer", email="import-policy-peer@example.test")
        self.business = Business.objects.create(owner=self.owner, name="Synthetic imports", slug="client-import-policy")
        self.role = BusinessRole.objects.create(business=self.business, name="Synthetic importer")
        self.member = BusinessMember.objects.create(business=self.business, user=self.actor, role="operator", business_role=self.role)
        self.peer_member = BusinessMember.objects.create(business=self.business, user=self.peer, role="operator")
        for resource in ("clients", "leads", "deals"):
            for action in ("view", "create", "update"):
                RolePermission.objects.create(business_role=self.role, resource=resource, action=action,
                    scope="business", is_allowed=action != "update")
        self.customer = Client.objects.create(business=self.business, full_name="Existing synthetic", phone="+77010001701")
        self.api = APIClient()
        self.api.force_authenticate(self.actor)

    def permission(self, action, allowed, scope="business"):
        RolePermission.objects.filter(business_role=self.role, resource="clients", action=action).update(is_allowed=allowed, scope=scope)

    def upload(self, rows, entity="clients"):
        stream = io.StringIO()
        headers = list(dict.fromkeys(k for row in rows for k in row))
        writer = csv.DictWriter(stream, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
        response = self.api.post("/api/import-jobs/", {"business": self.business.pk, "entity_type": entity,
            "source_file": SimpleUploadedFile("synthetic.csv", stream.getvalue().encode(), content_type="text/csv")}, format="multipart")
        self.assertEqual(response.status_code, 201, response.data)
        return ImportJob.objects.get(pk=response.data["id"])

    def confirm(self, job):
        return self.api.post(f"/api/import-jobs/{job.pk}/confirm/")

    def payload(self, **extra):
        return {"full_name": "Incoming name", "phone": self.customer.phone, "email": "new-field@example.test", **extra}

    def assert_denied_unchanged(self, job, before):
        response = self.confirm(job)
        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(Client.objects.values().get(pk=self.customer.pk), before)
        job.refresh_from_db()
        self.assertEqual(job.status, "previewed")
        self.assertFalse(BusinessEvent.objects.exists())
        self.assertFalse(ConnectorSyncRun.objects.exists())

    def test_create_only_cannot_fill_existing_client(self):
        job = self.upload([self.payload()])
        self.assert_denied_unchanged(job, Client.objects.values().get(pk=self.customer.pk))
        self.assertEqual(Client.objects.count(), 1)

    def test_archived_match_requires_update_and_never_creates_duplicate(self):
        Client.objects.filter(pk=self.customer.pk).update(is_archived=True, archive_reason="Synthetic archive")
        job = self.upload([self.payload()])
        self.assert_denied_unchanged(job, Client.objects.values().get(pk=self.customer.pk))
        self.assertEqual(Client.objects.count(), 1)

    def test_case_insensitive_email_match_requires_update(self):
        Client.objects.filter(pk=self.customer.pk).update(phone="", email="match@example.test")
        job = self.upload([{"full_name": "Incoming", "phone": "+77010001702", "email": "MATCH@example.test"}])
        self.assert_denied_unchanged(job, Client.objects.values().get(pk=self.customer.pk))

    def test_own_update_scope_matches_existing_unowned_client_policy(self):
        self.permission("update", True, "own")
        Lead.objects.create(business=self.business, client=self.customer, responsible_user=self.actor)
        self.assertTrue(can(self.actor, self.business, Resources.CLIENTS, Actions.UPDATE, obj=self.customer).allowed)
        self.assertEqual(self.api.patch(f"/api/clients/{self.customer.pk}/", {"source_detail": "Own control", "expected_updated_at": self.customer.updated_at.isoformat()}, format="json").status_code, 200)
        job = self.upload([self.payload()])
        self.assertEqual(self.confirm(job).status_code, 200)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.email, "new-field@example.test")

    def test_team_update_scope_matches_existing_unowned_client_policy(self):
        self.permission("update", True, "team")
        team = Team.objects.create(business=self.business, name="Synthetic import team")
        TeamMember.objects.create(team=team, member=self.member, is_lead=True)
        TeamMember.objects.create(team=team, member=self.peer_member)
        Lead.objects.create(business=self.business, client=self.customer, responsible_user=self.peer)
        self.assertTrue(can(self.actor, self.business, Resources.CLIENTS, Actions.UPDATE, obj=self.customer).allowed)
        self.assertEqual(self.api.patch(f"/api/clients/{self.customer.pk}/", {"source_detail": "Team control", "expected_updated_at": self.customer.updated_at.isoformat()}, format="json").status_code, 200)
        job = self.upload([self.payload()])
        self.assertEqual(self.confirm(job).status_code, 200)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.email, "new-field@example.test")

    def test_update_revoked_after_preview_is_rechecked(self):
        self.permission("update", True)
        job = self.upload([self.payload()])
        self.permission("update", False)
        self.assert_denied_unchanged(job, Client.objects.values().get(pk=self.customer.pk))

    def test_sensitive_note_denial_rolls_back_other_filled_fields(self):
        self.permission("update", True)
        job = self.upload([self.payload(notes="Synthetic private note")])
        self.assert_denied_unchanged(job, Client.objects.values().get(pk=self.customer.pk))

    def test_new_client_private_note_obeys_same_field_policy(self):
        job = self.upload([{"full_name": "New synthetic", "phone": "+77010001703", "notes": "Synthetic private note"}])
        response = self.confirm(job)
        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(Client.objects.count(), 1)
        self.assertFalse(BusinessEvent.objects.exists())

    def test_mixed_file_denial_rolls_back_earlier_new_client(self):
        job = self.upload([{"full_name": "New first", "phone": "+77010001704"}, self.payload()])
        self.assert_denied_unchanged(job, Client.objects.values().get(pk=self.customer.pk))
        self.assertEqual(Client.objects.count(), 1)

    def test_lead_import_cannot_mutate_existing_client_through_shared_helper(self):
        job = self.upload([self.payload(message="Synthetic lead")], entity="leads")
        self.assert_denied_unchanged(job, Client.objects.values().get(pk=self.customer.pk))
        self.assertFalse(Lead.objects.exists())

    def test_deal_import_cannot_mutate_existing_client_through_shared_helper(self):
        job = self.upload([{"title": "Synthetic deal", "phone": self.customer.phone, "email": "new-field@example.test", "amount": "10"}], entity="deals")
        self.assert_denied_unchanged(job, Client.objects.values().get(pk=self.customer.pk))
        self.assertFalse(Deal.objects.exists())

    def test_no_actor_low_level_fill_fails_closed_without_in_memory_changes(self):
        before = self.customer.email
        with self.assertRaises(PermissionDenied):
            fill_missing_client_fields(self.customer, self.payload())
        self.assertEqual(self.customer.email, before)

    def test_direct_row_requires_create_for_new_client(self):
        self.permission("create", False)
        job = ImportJob(business=self.business, actor=self.actor, entity_type="clients")
        with self.assertRaises(PermissionDenied):
            import_client_row(job, {"full_name": "Synthetic blocked new", "phone": "+77010001705"})
        self.assertEqual(Client.objects.count(), 1)

    def test_new_client_create_only_legitimate_control(self):
        job = self.upload([{"full_name": "New legitimate", "phone": "+77010001706", "notes": ""}])
        response = self.confirm(job)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["summary_json"]["created"], 1)
        self.assertEqual(Client.objects.count(), 2)

    def test_allowed_update_fills_only_missing_fields(self):
        self.permission("update", True)
        Client.objects.filter(pk=self.customer.pk).update(source="other")
        job = self.upload([self.payload(source="website")])
        response = self.confirm(job)
        self.assertEqual(response.status_code, 200, response.data)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.full_name, "Existing synthetic")
        self.assertEqual(self.customer.email, "new-field@example.test")
        self.assertEqual(self.customer.source, "website")
        self.assertEqual(response.data["summary_json"]["updated"], 1)

    def test_masked_empty_notes_preserve_existing_private_note(self):
        self.permission("update", True)
        Client.objects.filter(pk=self.customer.pk).update(notes="Stored synthetic note")
        job = self.upload([self.payload(notes="")])
        response = self.confirm(job)
        self.assertEqual(response.status_code, 200, response.data)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.notes, "Stored synthetic note")
        self.assertEqual(self.customer.email, "new-field@example.test")

    def test_owner_updates_archived_without_restoring_or_overwriting(self):
        self.api.force_authenticate(self.owner)
        Client.objects.filter(pk=self.customer.pk).update(is_archived=True, notes="Stored owner note")
        job = self.upload([self.payload(notes="Ignored nonempty replacement")])
        response = self.confirm(job)
        self.assertEqual(response.status_code, 200, response.data)
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.is_archived)
        self.assertEqual(self.customer.notes, "Stored owner note")
        self.assertEqual(self.customer.email, "new-field@example.test")

    def test_foreign_business_match_does_not_authorize_or_mutate_foreign_client(self):
        foreign = Business.objects.create(owner=self.owner, name="Other synthetic", slug="foreign-import-policy")
        BusinessMember.objects.create(business=foreign, user=self.actor, role="admin")
        other = Client.objects.create(business=foreign, full_name="Foreign", phone="+77010001707")
        job = self.upload([{"full_name": "Own new", "phone": other.phone, "email": "own-new@example.test"}])
        response = self.confirm(job)
        self.assertEqual(response.status_code, 200, response.data)
        other.refresh_from_db()
        self.assertEqual(other.email, "")
        self.assertTrue(Client.objects.filter(business=self.business, phone=other.phone).exists())

    def test_current_request_not_stored_creator_controls_all_row_variants(self):
        job = ImportJob(business=self.business, actor=self.owner)
        for importer in (import_client_row, import_lead_row, import_deal_row):
            with self.subTest(importer=importer.__name__):
                with self.assertRaises(PermissionDenied):
                    importer(job, self.payload(title="Synthetic deal", amount="10", message="Synthetic lead"),
                             request=SimpleNamespace(user=self.actor))
                self.customer.refresh_from_db()
                self.assertEqual(self.customer.email, "")

    def test_authorized_current_request_control_ignores_creator_authority(self):
        job = ImportJob(business=self.business, actor=self.actor)
        result = import_client_row(job, self.payload(), request=SimpleNamespace(user=self.owner))
        self.assertEqual(result, "updated")
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.email, "new-field@example.test")

    def test_sibling_new_client_branches_require_client_create(self):
        self.permission("create", False)
        job = ImportJob(business=self.business, actor=self.actor)
        for importer in (import_lead_row, import_deal_row):
            with self.subTest(importer=importer.__name__):
                with self.assertRaises(PermissionDenied):
                    importer(job, {"full_name": "Synthetic new", "phone": "+77010001708", "title": "Synthetic deal",
                                   "amount": "10", "message": "Synthetic lead"})
        self.assertEqual(Client.objects.count(), 1)
        self.assertFalse(Lead.objects.exists())
        self.assertFalse(Deal.objects.exists())

    def test_note_denial_preserves_in_memory_and_persisted_public_fields(self):
        self.permission("update", True)
        with self.assertRaises(PermissionDenied):
            fill_missing_client_fields(self.customer, self.payload(notes="Synthetic denied note"), actor=self.actor)
        self.assertEqual(self.customer.email, "")
        self.assertEqual(self.customer.notes, "")
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.email, "")

    def test_sensitive_field_rights_are_current_at_confirm(self):
        self.permission("update", True)
        self.member.role = "manager"
        self.member.save(update_fields=["role"])
        job = self.upload([self.payload(notes="Synthetic note")])
        self.member.role = "operator"
        self.member.save(update_fields=["role"])
        self.assert_denied_unchanged(job, Client.objects.values().get(pk=self.customer.pk))

    def test_owner_can_fill_and_create_private_notes(self):
        self.api.force_authenticate(self.owner)
        job = self.upload([self.payload(notes="Allowed existing note"),
            {"full_name": "Owner new", "phone": "+77010001709", "notes": "Allowed new note"}])
        response = self.confirm(job)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["summary_json"]["created"], 1)
        self.assertEqual(response.data["summary_json"]["updated"], 1)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.notes, "Allowed existing note")
        self.assertEqual(Client.objects.get(phone="+77010001709").notes, "Allowed new note")

    def test_existing_row_uses_update_not_create_at_mutation_boundary(self):
        self.permission("update", True)
        self.permission("create", False)
        job = ImportJob(business=self.business, actor=self.actor)
        self.assertEqual(import_client_row(job, self.payload()), "updated")
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.email, "new-field@example.test")

    def test_existing_noop_match_still_requires_update(self):
        job = self.upload([{"full_name": self.customer.full_name, "phone": self.customer.phone}])
        self.assert_denied_unchanged(job, Client.objects.values().get(pk=self.customer.pk))

    def test_new_client_scope_matches_direct_api_candidate_policy(self):
        for scope in ("own", "team"):
            with self.subTest(scope=scope):
                self.permission("create", True, scope)
                candidate = Client(business=self.business, full_name="Synthetic scoped new")
                self.assertFalse(can(self.actor, self.business, Resources.CLIENTS, Actions.CREATE, obj=candidate).allowed)
                direct = self.api.post("/api/clients/", {"business": self.business.pk, "full_name": "Scoped direct"}, format="json")
                self.assertEqual(direct.status_code, 403, direct.data)
                job = self.upload([{"full_name": "Scoped import", "phone": "+77010001710"}])
                self.assertEqual(self.confirm(job).status_code, 403)
                self.assertEqual(Client.objects.count(), 1)

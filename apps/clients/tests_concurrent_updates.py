from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.activities.models import ActivityEvent
from apps.businesses.models import Business, BusinessMember
from apps.clients.models import Client
from apps.core.models import AuditLog


class ClientConcurrentUpdateTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="edit-owner", email="edit-owner@example.test", password="pass")
        self.business = Business.objects.create(owner=self.owner, name="Edit A", slug="edit-a")
        BusinessMember.objects.create(business=self.business, user=self.owner, role=BusinessMember.Roles.OWNER)
        self.customer = Client.objects.create(business=self.business, full_name="Synthetic client")
        self.api = APIClient()
        self.api.force_authenticate(self.owner)
        self.url = f"/api/clients/{self.customer.pk}/"

    def snapshot(self):
        response = self.api.get(self.url)
        self.assertEqual(response.status_code, 200)
        return response.data["updated_at"]

    def save(self, version, **values):
        return self.api.patch(self.url, {"expected_updated_at": version, **values}, format="json")

    def test_two_editors_preserve_first_write_and_allow_explicit_retry(self):
        version = self.snapshot()
        first = self.save(version, source_detail="Tab A")
        self.assertEqual(first.status_code, 200)
        counts = (AuditLog.objects.count(), ActivityEvent.objects.count())
        stale = self.save(version, source_detail="", notes="Tab B")
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.data["code"], "client_edit_conflict")
        self.assertEqual((AuditLog.objects.count(), ActivityEvent.objects.count()), counts)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.source_detail, "Tab A")
        self.assertEqual(self.customer.notes, "")
        retry = self.save(first.data["updated_at"], notes="Tab B")
        self.assertEqual(retry.status_code, 200)
        self.customer.refresh_from_db()
        self.assertEqual((self.customer.source_detail, self.customer.notes), ("Tab A", "Tab B"))

    def test_same_field_stale_write_is_rejected(self):
        version = self.snapshot()
        self.assertEqual(self.save(version, full_name="First winner").status_code, 200)
        self.assertEqual(self.save(version, full_name="Lost update").status_code, 409)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.full_name, "First winner")

    def test_patch_and_put_require_precondition(self):
        for method in (self.api.patch, self.api.put):
            response = method(self.url, {"business": self.business.pk, "full_name": "No snapshot"}, format="json")
            self.assertEqual(response.status_code, 400)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.full_name, "Synthetic client")

    def test_write_after_api_read_before_save_is_detected_atomically(self):
        from apps.clients.updates import update_client_snapshot

        version = self.snapshot()

        def interleaved_write(**kwargs):
            other_snapshot = Client.objects.get(pk=self.customer.pk)
            update_client_snapshot(client=other_snapshot, expected_updated_at=other_snapshot.updated_at,
                                   values={"source_detail": "Concurrent writer"})
            return update_client_snapshot(**kwargs)

        with patch("apps.clients.updates.update_client_snapshot", side_effect=interleaved_write):
            response = self.save(version, notes="Stale editor")
        self.assertEqual(response.status_code, 409)
        # The injected writer shares this request's transaction; both roll back.
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.notes, "")
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_invalid_and_future_preconditions_do_not_write(self):
        for value, status in (("not-a-date", 400), ("9999-12-31T23:59:59.999999Z", 409)):
            self.assertEqual(self.save(value, notes="Rejected").status_code, status)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.notes, "")

    def test_success_preserves_identity_normalization_and_advances_version(self):
        version = self.snapshot()
        response = self.save(version, phone="+7 (701) 555-01-01", email="HELLO@example.com")
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.data["updated_at"], version)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.normalized_phone, "77015550101")
        self.assertEqual(self.customer.normalized_email, "hello@example.com")

    def test_audit_failure_rolls_back_metadata(self):
        version = self.snapshot()
        with patch("apps.core.viewsets.write_audit_log", side_effect=RuntimeError("audit failure")):
            self.assertEqual(self.save(version, notes="Must roll back").status_code, 500)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.notes, "")
        self.assertEqual(self.snapshot(), version)

    def test_foreign_business_and_read_only_role_cannot_write(self):
        version = self.snapshot()
        other = User.objects.create_user(username="other-editor", email="other-editor@example.test", password="pass")
        foreign = Business.objects.create(owner=other, name="Edit B", slug="edit-b")
        BusinessMember.objects.create(business=foreign, user=other, role=BusinessMember.Roles.OWNER)
        self.api.force_authenticate(other)
        self.assertIn(self.save(version, notes="Foreign").status_code, (403, 404))
        BusinessMember.objects.create(business=self.business, user=other, role=BusinessMember.Roles.MARKETER)
        self.assertIn(self.save(version, notes="Forbidden").status_code, (403, 404))
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.notes, "")

from unittest.mock import patch
from unittest import skipUnless
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pyotp
from django.db import OperationalError, connection, connections, close_old_connections
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient, APIRequestFactory

from apps.accounts.mfa import issue_step_up_token
from apps.accounts.models import MfaDevice, User
from apps.businesses.models import Business, BusinessMember
from apps.businesses.serializers import BusinessSerializer
from apps.businesses.views import BusinessViewSet
from apps.core.models import AuditLog
from apps.core.platform_details import DETAIL_FIELDS
from apps.integrations.credential_encryption import encrypt_credential_value
from apps.support.models import SupportCase


class PlatformDetailsTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="details-owner", email="details-owner@example.com", role="business_owner")
        self.actor = User.objects.create_user(username="details-operator", email="details-operator@example.com", role="platform_manager")
        self.business = Business.objects.create(owner=self.owner, name="Business", slug="details-business")
        BusinessMember.objects.create(business=self.business, user=self.owner, role="owner")
        self.case = SupportCase.objects.create(business=self.business, created_by=self.owner,
            requester=self.owner, subject="Correct details", source="clinic")
        secret = pyotp.random_base32()
        MfaDevice.objects.create(user=self.actor, encrypted_secret=encrypt_credential_value(secret), confirmed_at=timezone.now())
        self.token = issue_step_up_token(self.actor, pyotp.TOTP(secret).now())
        self.api = APIClient()
        self.api.force_authenticate(self.actor)
        self.url = f"/api/platform/merchants/{self.business.pk}/details/"
        self.payload = {"changes": {"name": "Corrected", "invoice_email": "billing@example.com"},
                        "expected_revision": self.api.get(self.url).data["revision"],
                        "support_case_id": self.case.pk, "reason": "Verified correction request"}

    def save(self, payload=None, token=None):
        return self.api.patch(self.url, payload or self.payload, format="json",
            HTTP_X_ZANI_MFA_STEP_UP=self.token if token is None else token)

    def test_both_roles_correct_without_grant_and_audit_safe_metadata(self):
        for role in ("platform_manager", "platform_admin"):
            self.actor.role = role
            self.actor.save(update_fields=["role"])
            self.payload["changes"]["name"] = role
            response = self.save()
            self.assertEqual(response.status_code, 200, response.data)
            self.assertIn("no-store", response["Cache-Control"])
            self.payload["expected_revision"] = response.data["revision"]
        audit = AuditLog.objects.filter(metadata__kind="platform_business_details").latest("pk")
        self.assertEqual(audit.actor_id, self.actor.pk)
        self.assertEqual(audit.metadata["support_case_id"], self.case.pk)
        self.assertEqual(audit.metadata["reason"], self.payload["reason"])
        self.assertNotIn("billing@example.com", str(audit.metadata))
        self.business.refresh_from_db()
        self.assertEqual(self.business.owner_id, self.owner.pk)
        self.assertEqual(self.business.status, "trial")
        self.case.refresh_from_db()
        self.assertEqual(self.case.version, 1)

    def test_read_allowlist_and_audit(self):
        response = self.api.get(self.url)
        self.assertEqual(set(response.data["details"]), set(DETAIL_FIELDS))
        self.assertIn("no-store", response["Cache-Control"])
        self.assertTrue(AuditLog.objects.filter(metadata__resource="business_details").exists())

    def test_correction_history_is_scoped_and_contains_no_contact_values(self):
        self.assertEqual(self.save().status_code, 200)
        response = self.api.get(f"/api/platform/merchants/{self.business.pk}/crm-access-log/")
        correction = next(row["correction"] for row in response.data["results"] if "correction" in row)
        self.assertEqual(correction["changed_fields"], ["invoice_email", "name"])
        self.assertEqual(correction["support_case_id"], self.case.pk)
        self.assertNotIn("billing@example.com", str(response.data))
        other = Business.objects.create(owner=self.owner, name="No history", slug="details-history-other")
        response = self.api.get(f"/api/platform/merchants/{other.pk}/crm-access-log/")
        self.assertEqual(response.data["count"], 0)

    def test_invalid_payloads_and_forbidden_fields(self):
        for changes in ({}, {"name": " "}, {"name": "a" * 256}, {"invoice_email": "bad"},
                        {"owner": self.owner.pk}, {"status": "blocked"}, {"tax_id": None}):
            with self.subTest(changes=changes):
                self.assertEqual(self.save({**self.payload, "changes": changes}).status_code, 400)
        for delta in ({"extra": "bad"}, {"reason": " "}, {"support_case_id": 0}):
            self.assertEqual(self.save({**self.payload, **delta}).status_code, 400)
        self.assertFalse(AuditLog.objects.filter(metadata__kind="platform_business_details").exists())

    def test_optional_fields_clear_and_tax_id_remains_universal(self):
        self.payload["changes"] = {"phone": "", "legal_name": "", "tax_id": "FOREIGN-42"}
        self.assertEqual(self.save().status_code, 200)

    def test_merchant_inactive_and_stale_role_denied(self):
        self.api.force_authenticate(self.owner)
        self.assertEqual(self.save().status_code, 403)
        self.assertEqual(self.api.get(self.url).status_code, 403)
        self.api.force_authenticate(self.actor)
        for update in ({"is_active": False}, {"is_active": True, "role": "manager"}):
            User.objects.filter(pk=self.actor.pk).update(**update)
            self.assertEqual(self.save().status_code, 403)
            self.assertEqual(self.api.get(self.url).status_code, 403)

    def test_missing_bad_expired_foreign_and_revoked_mfa(self):
        for token in ("", "invalid"):
            self.assertEqual(self.save(token=token).status_code, 401)
        with override_settings(AUTH_MFA_STEP_UP_SECONDS=-1):
            self.assertEqual(self.save().status_code, 401)
        other = User.objects.create_user(username="other-platform", email="other-platform@example.com", role="platform_manager")
        MfaDevice.objects.create(user=other, encrypted_secret=encrypt_credential_value(pyotp.random_base32()), confirmed_at=timezone.now())
        self.api.force_authenticate(other)
        self.assertEqual(self.save().status_code, 401)
        self.api.force_authenticate(self.actor)
        User.objects.filter(pk=self.actor.pk).update(auth_epoch=self.actor.auth_epoch + 1)
        self.assertEqual(self.save().status_code, 401)

    def test_foreign_case_denied(self):
        other = Business.objects.create(owner=self.owner, name="Other", slug="details-other")
        SupportCase.objects.filter(pk=self.case.pk).update(business=other)
        self.assertEqual(self.save().status_code, 404)
        self.business.refresh_from_db()
        self.assertEqual(self.business.name, "Business")

    def test_audit_failure_rolls_back_and_read_fails_closed(self):
        with patch("apps.core.platform_details.write_audit_log", side_effect=OperationalError("unavailable")):
            self.assertEqual(self.save().status_code, 503)
        self.business.refresh_from_db()
        self.assertEqual(self.business.name, "Business")
        with patch("apps.core.platform_crm_views.write_audit_log", side_effect=OperationalError("unavailable")):
            self.assertEqual(self.api.get(self.url).status_code, 503)

    def test_merchant_update_conflicts_and_replay_does_not_write_twice(self):
        self.api.force_authenticate(self.owner)
        result = self.api.patch(f"/api/businesses/{self.business.pk}/", {"name": "Merchant correction"}, format="json")
        self.assertEqual(result.status_code, 200, result.data)
        self.api.force_authenticate(self.actor)
        conflict = self.save()
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.data["category"], "conflict")
        self.payload["expected_revision"] = self.api.get(self.url).data["revision"]
        self.assertEqual(self.save().status_code, 200)
        self.assertEqual(self.save().status_code, 409)
        self.assertEqual(AuditLog.objects.filter(metadata__kind="platform_business_details").count(), 1)

    def test_merchant_serializer_loaded_before_correction_preserves_other_details(self):
        serializer = BusinessSerializer(self.business, data={"city": "New city"}, partial=True)
        serializer.is_valid(raise_exception=True)
        self.assertEqual(self.save().status_code, 200)
        view = BusinessViewSet()
        view.request = APIRequestFactory().patch("/")
        view.request.user = self.owner
        view.perform_update(serializer)
        self.business.refresh_from_db()
        self.assertEqual(self.business.name, "Corrected")
        self.assertEqual(self.business.city, "New city")


@skipUnless(connection.vendor == "postgresql", "Row locking requires isolated PostgreSQL.")
class PlatformDetailsConcurrencyTests(TransactionTestCase):
    setUp = PlatformDetailsTests.setUp

    def test_two_corrections_with_same_revision_have_one_winner(self):
        barrier = Barrier(2)

        def save(index):
            close_old_connections()
            try:
                client = APIClient()
                client.force_authenticate(self.actor)
                barrier.wait(timeout=10)
                return client.patch(self.url, {**self.payload, "changes": {"name": f"Winner {index}"}},
                    format="json", HTTP_X_ZANI_MFA_STEP_UP=self.token).status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(save, (0, 1)))
        self.assertCountEqual(results, [200, 409])
        self.assertEqual(AuditLog.objects.filter(metadata__kind="platform_business_details").count(), 1)

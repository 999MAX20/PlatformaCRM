import copy
from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from apps.businesses.models import Business
from . import tests_tooth_services as fixtures
from .tests_patient_services import key
from .models import MedicalAuditEvent
from .audit import MedicalAuditUnavailable
from .tooth_policy import ToothNotationUnavailable, surface_evidence
from .tooth_reads import read_tooth_surface_options
from .tooth_content import read_tooth_history


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8), MEDICAL_TOOTH_SURFACE_POLICIES="")
class ToothSurfaceOptionsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.PrimaryToothObservationTests.setUpTestData.__func__(cls)

    save = fixtures.PrimaryToothObservationTests.save

    def policy(self):
        return {str(self.business.pk): {"reference": "synthetic-v1", "approval_reference": "internal-test-only",
            "teeth": {"11": ["synthetic_a"], "51": ["synthetic_b"]},
            "labels": {code: {"ru": f"Тест {code}", "kk": f"Сынақ {code}", "en": f"Test {code}"}
                for code in ["synthetic_a", "synthetic_b"]}}}

    def read(self, **overrides):
        return read_tooth_surface_options(**(dict(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, tooth=11, appointment_id=self.appointment.pk) | overrides))

    def test_missing_policy_returns_audited_disabled_choices(self):
        result = self.read()
        self.assertEqual(result, {"tooth": 11, "configured": False, "reference": None, "surfaces": []})
        self.assertEqual(MedicalAuditEvent.objects.get().action, "read")
        with self.assertRaises(ToothNotationUnavailable):
            surface_evidence(business_id=self.business.pk, tooth=11, surface="synthetic_a", reference="synthetic-v1")
        self.save()  # Whole tooth remains independently writable.

    def test_configured_choices_are_scoped_to_tooth_and_hide_internal_approval(self):
        with override_settings(MEDICAL_TOOTH_SURFACE_POLICIES=self.policy()):
            result = self.read()
            self.assertEqual([item["code"] for item in result["surfaces"]], ["synthetic_a"])
            self.assertEqual(set(result["surfaces"][0]["labels"]), {"ru", "kk", "en"})
            self.assertNotIn("internal-test-only", str(result))
            self.assertEqual(self.read(tooth=51)["surfaces"][0]["code"], "synthetic_b")
            self.assertEqual(self.read(tooth=12)["surfaces"], [])
            saved, _ = self.save(surface="synthetic_a", surface_reference=result["reference"])
            self.assertEqual(read_tooth_history(saved)["surface_protocol"]["approval_reference"], "internal-test-only")

    def test_legacy_code_only_policy_remains_readable_and_writable(self):
        policy = self.policy()
        del policy[str(self.business.pk)]["labels"]
        with override_settings(MEDICAL_TOOTH_SURFACE_POLICIES=policy):
            self.assertEqual(self.read()["surfaces"][0]["labels"], {})
            self.save(surface="synthetic_a", surface_reference="synthetic-v1")

    def test_malformed_policy_and_partial_labels_fail_closed(self):
        original = self.policy()
        for change in ({"labels": {}}, {"labels": {"synthetic_a": {"ru": "Only one"}}},
                       {"approval_reference": ""}, {"unexpected": "field"},
                       {"teeth": {"19": ["synthetic_a"]}}):
            policy = copy.deepcopy(original)
            policy[str(self.business.pk)].update(change)
            with self.subTest(change=change), override_settings(MEDICAL_TOOTH_SURFACE_POLICIES=policy):
                with self.assertRaises(ToothNotationUnavailable): self.read()
                with self.assertRaises(ToothNotationUnavailable):
                    self.save(surface="synthetic_a", surface_reference="synthetic-v1")
        for value in ("invalid json", "[]", None):
            with override_settings(MEDICAL_TOOTH_SURFACE_POLICIES=value), self.assertRaises(ToothNotationUnavailable):
                self.read()
        self.assertFalse(MedicalAuditEvent.objects.exists())

    def test_foreign_policy_is_not_used_as_fallback(self):
        policy = self.policy()
        policy["999999"] = policy.pop(str(self.business.pk))
        with override_settings(MEDICAL_TOOTH_SURFACE_POLICIES=policy):
            self.assertFalse(self.read()["configured"])
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="surface-options-foreign")
        with self.assertRaises(PermissionDenied): self.read(business_id=foreign.pk)

    def test_revoked_or_owner_role_denied(self):
        with self.assertRaises(PermissionDenied): self.read(actor=self.owner)
        type(self.assignment).objects.filter(pk=self.assignment.pk).update(revoked_at=timezone.now())
        with self.assertRaises(PermissionDenied): self.read()
        self.assertFalse(MedicalAuditEvent.objects.exists())

    def test_invalid_tooth_and_missing_basis_are_rejected(self):
        for change in ({"tooth": 19}, {"tooth": True}, {"appointment_id": None}):
            with self.subTest(change=change), self.assertRaises(ValidationError): self.read(**change)

    def test_audit_failure_prevents_response(self):
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError):
            with self.assertRaises(MedicalAuditUnavailable): self.read()

    def test_http_scope_strictness_and_cache_headers(self):
        api = APIClient()
        api.force_authenticate(self.doctor)
        path = "/api/medical/tooth-observations/surface-options/"
        params = dict(business_id=self.business.pk, patient_id=self.patient.pk, appointment_id=self.appointment.pk, tooth=11)
        with override_settings(MEDICAL_TOOTH_SURFACE_POLICIES=self.policy()):
            response = api.get(path, params)
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data["surfaces"][0]["code"], "synthetic_a")
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(response["Pragma"], "no-cache")
        for change in ({"tooth": 19}, {"author_id": self.owner.pk}):
            response = api.get(path, params | change)
            self.assertEqual(response.status_code, 400, response.data)
        api.force_authenticate(None)
        response = api.get(path, params)
        self.assertIn(response.status_code, (401, 403))
        self.assertEqual(response["Cache-Control"], "no-store, private")

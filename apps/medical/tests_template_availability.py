from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.businesses.models import Business, RolePermission
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandConflict
from . import tests_template_search as fixtures
from .audit import MedicalAuditUnavailable
from .common_template_services import list_approved_templates, read_approved_template_version
from .identity_crypto import MedicalDataUnavailable
from .models import MedicalAuditEvent, MedicalDocumentTemplate, MedicalTemplateAvailabilityRevision
from .template_availability import list_managed_templates, list_template_availability, set_template_availability
from .template_services import save_personal_template_draft
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class TemplateAvailabilityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.TemplateSearchTests.setUpTestData.__func__(cls)

    create = fixtures.TemplateSearchTests.create

    def setUp(self):
        self.version = self.create("availability")

    def change(self, **overrides):
        return set_template_availability(**(dict(actor=self.head, business_id=self.business.pk,
            template_id=self.version.template_id, is_active=False, expected_revision=0,
            reason="Synthetic private reason", idempotency_key="pause") | overrides))

    def history(self, **overrides):
        return list_template_availability(**(dict(actor=self.head, business_id=self.business.pk,
            template_id=self.version.template_id) | overrides))

    def test_pause_resume_retains_approved_snapshot_and_encrypted_history(self):
        original = self.version.snapshot_encrypted
        change, replayed = self.change()
        self.assertFalse(replayed)
        self.assertNotIn("Synthetic private reason", change.reason_encrypted)
        self.assertEqual(list_approved_templates(actor=self.doctor, business_id=self.business.pk)["results"], [])
        with self.assertRaises(InvalidTransition):
            read_approved_template_version(actor=self.doctor, business_id=self.business.pk, version_id=self.version.pk)
        self.change(is_active=True, expected_revision=1, idempotency_key="resume")
        self.assertEqual(len(list_approved_templates(actor=self.doctor, business_id=self.business.pk)["results"]), 1)
        first = self.history(limit=1)
        self.assertTrue(first["is_active"])
        self.assertEqual(first["results"][0]["revision"], 2)
        second = self.history(limit=1, before_revision=first["next_before_revision"])
        self.assertEqual(second["results"][0]["reason"], "Synthetic private reason")
        self.assertFalse(second["results"][0]["is_active"])
        self.version.refresh_from_db()
        self.assertEqual(self.version.snapshot_encrypted, original)
        self.assertEqual(MedicalAuditEvent.objects.filter(template_availability__isnull=False,
            action__in=["template_activated", "template_deactivated"]).count(), 2)

    def test_resume_does_not_approve_new_draft(self):
        draft, _ = save_personal_template_draft(actor=self.doctor, business_id=self.business.pk,
            template_id=self.version.template_id, expected_revision=1, title="Changed", text="New",
            idempotency_key="draft")
        self.change()
        self.change(is_active=True, expected_revision=1, idempotency_key="resume")
        rows = list_approved_templates(actor=self.doctor, business_id=self.business.pk)["results"]
        self.assertEqual([row["version_id"] for row in rows], [self.version.pk])
        with self.assertRaises(PermissionDenied):
            read_approved_template_version(actor=self.doctor, business_id=self.business.pk, version_id=draft.pk)

    def test_replay_conflict_stale_and_current_permission(self):
        first, _ = self.change()
        replay, replayed = self.change()
        self.assertTrue(replayed)
        self.assertEqual(first.pk, replay.pk)
        with self.assertRaises(CRMCommandConflict):
            self.change(reason="Different")
        with self.assertRaises(InvalidTransition):
            self.change(idempotency_key="stale")
        with self.assertRaises(InvalidTransition):
            self.change(expected_revision=1, idempotency_key="same-state")
        RolePermission.objects.filter(business_role=self.head_role, action="approve").update(is_allowed=False)
        with self.assertRaises(PermissionDenied):
            self.change()
        self.assertEqual(MedicalTemplateAvailabilityRevision.objects.count(), 1)

    def test_doctor_owner_foreign_and_unsubmitted_personal_denied(self):
        for actor in (self.doctor, self.owner):
            with self.subTest(actor=actor.pk), self.assertRaises(PermissionDenied):
                self.change(actor=actor)
            with self.assertRaises(PermissionDenied):
                self.history(actor=actor)
        business = Business.objects.create(owner=self.owner, name="Other", slug="availability-other")
        foreign = MedicalDocumentTemplate.objects.create(business=business, code="foreign")
        with self.assertRaises(PermissionDenied):
            self.change(template_id=foreign.pk)
        unsubmitted = self.create("unsubmitted", approved=False)
        with self.assertRaises(PermissionDenied):
            self.change(template_id=unsubmitted.template_id)

    def test_audit_failure_rolls_back_activity_and_history(self):
        with patch("apps.medical.template_availability._audit", side_effect=MedicalAuditUnavailable), self.assertRaises(MedicalAuditUnavailable):
            self.change()
        template = MedicalDocumentTemplate.objects.get(pk=self.version.template_id)
        self.assertTrue(template.is_active)
        self.assertEqual(template.availability_revision, 0)
        self.assertFalse(MedicalTemplateAvailabilityRevision.objects.exists())
        self.assertFalse(self.change()[1])

    def test_corrupted_reason_fails_closed_and_rolls_back_read_audit(self):
        change, _ = self.change()
        MedicalTemplateAvailabilityRevision.objects.filter(pk=change.pk).update(reason_encrypted="corrupt")
        count = MedicalAuditEvent.objects.count()
        with self.assertRaises(MedicalDataUnavailable):
            self.history()
        self.assertEqual(MedicalAuditEvent.objects.count(), count)

    def test_invalid_commands_do_not_mutate(self):
        for kwargs in ({"reason": " "}, {"reason": "x" * 2001}, {"is_active": 0},
                       {"expected_revision": True}, {"expected_revision": -1}, {"idempotency_key": ""}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValidationError):
                self.change(**kwargs)
        self.assertFalse(MedicalTemplateAvailabilityRevision.objects.exists())

    def test_management_lists_latest_approved_with_activity_and_search(self):
        common = self.create("common", common=True)
        self.create("unsubmitted", approved=False)
        self.change()
        rows = list_managed_templates(actor=self.head, business_id=self.business.pk, activity="inactive", q="availability")["results"]
        self.assertEqual([row["version_id"] for row in rows], [self.version.pk])
        self.assertEqual(rows[0]["availability"], {"is_active": False, "revision": 1})
        active = list_managed_templates(actor=self.head, business_id=self.business.pk, activity="active")["results"]
        self.assertEqual([row["version_id"] for row in active], [common.pk])
        with self.assertRaises(PermissionDenied):
            list_managed_templates(actor=self.doctor, business_id=self.business.pk)
        with self.assertRaises(ValidationError):
            list_managed_templates(actor=self.head, business_id=self.business.pk, activity="bad")

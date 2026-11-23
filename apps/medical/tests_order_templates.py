from unittest.mock import patch

from django.db import DatabaseError
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from apps.businesses.models import RolePermission
from apps.core.domain_errors import InvalidTransition
from . import tests_document_template_source as fixtures
from . import tests_patient_services as crypto
from .audit import MedicalAuditUnavailable
from .identity_crypto import MedicalDataUnavailable
from .models import MedicalOrder, MedicalOrderRevision
from .order_content import read_order_revision
from .order_services import save_order_draft
from .order_templates import preview_order_template
from .template_availability import set_template_availability


@override_settings(MEDICAL_DATA_KEYS={"test": crypto.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto.key(8))
class OrderTemplateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.DocumentTemplateSourceTests.setUpTestData.__func__(cls)
        for action in ("view", "create", "update"):
            RolePermission.objects.get_or_create(business_role=cls.role, resource="medical_prescriptions",
                action=action, defaults={"scope": "own", "is_allowed": True})

    def setUp(self):
        fixtures.DocumentTemplateSourceTests.setUp(self)
        fixtures.DocumentTemplateSourceTests.approve(self)

    def preview(self, **overrides):
        return preview_order_template(**(dict(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, encounter_id=self.encounter_record.pk,
            appointment_id=self.appointment.pk, template_version_id=self.template.pk) | overrides))

    def save(self, **overrides):
        digest = overrides["expected_source_digest"] if "expected_source_digest" in overrides else self.preview()["template_source"]["source_digest"]
        return save_order_draft(**(dict(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, encounter_id=self.encounter_record.pk,
            expected_encounter_revision=1, expected_patient_revision=self.patient.revision,
            content={"kind": "medication", "text": "Doctor edited synthetic text", "medication": {"dose": "Manual dose"}},
            template_version_id=self.template.pk,
            expected_source_digest=digest,
            idempotency_key="order-template") | overrides))

    def test_preview_save_replay_exact_provenance_and_manual_fields(self):
        preview = self.preview()
        self.assertEqual(preview["document_text"], "Original {{patient}} text")
        self.assertFalse(MedicalOrder.objects.exists())
        version, replayed = self.save()
        self.assertFalse(replayed)
        self.assertEqual(self.save()[0].pk, version.pk)
        data = read_order_revision(version)
        self.assertEqual(data["content"]["medication"], {"dose": "Manual dose"})
        self.assertEqual(data["template_source"], preview["template_source"])
        self.assertEqual(data["content"]["text"], "Doctor edited synthetic text")
        self.assertNotIn("Synthetic", version.content_encrypted)
        with self.assertRaises(ProtectedError):
            version.source_version.delete()

    def test_plain_edit_retains_source_after_pause_without_reapplying(self):
        first, _ = self.save()
        source = read_order_revision(first)["template_source"]
        set_template_availability(actor=self.head, business_id=self.business.pk,
            template_id=self.template.template_id, is_active=False, expected_revision=0,
            reason="Synthetic pause", idempotency_key="pause")
        with self.assertRaises(InvalidTransition):
            self.preview()
        with self.assertRaises(InvalidTransition):
            self.save(expected_source_digest=source["source_digest"])
        second, _ = save_order_draft(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, encounter_id=self.encounter_record.pk,
            expected_encounter_revision=1, expected_patient_revision=self.patient.revision,
            order_id=first.order_id, expected_order_revision=1, idempotency_key="edit",
            content={"kind": "other", "text": "Later manual edit", "medication": {}})
        self.assertEqual(read_order_revision(second)["template_source"], source)
        self.assertEqual(read_order_revision(first)["content"]["text"], "Doctor edited synthetic text")

    def test_stale_source_and_missing_digest_do_not_create_order(self):
        digest = self.preview()["template_source"]["source_digest"]
        self.business.name = "Changed synthetic clinic"
        self.business.save(update_fields=["name"])
        with self.assertRaises(InvalidTransition):
            self.save(expected_source_digest=digest)
        with self.assertRaises(ValidationError):
            self.save(expected_source_digest=None)
        self.assertFalse(MedicalOrder.objects.exists())

    def test_medical_read_and_prescription_acl_are_both_required(self):
        for resource in ("medical_records", "medical_prescriptions"):
            permission = RolePermission.objects.get(business_role=self.role, resource=resource, action="view")
            permission.is_allowed = False; permission.save(update_fields=["is_allowed"])
            with self.subTest(resource=resource), self.assertRaises(PermissionDenied):
                self.preview()
            permission.is_allowed = True; permission.save(update_fields=["is_allowed"])
        with self.assertRaises(PermissionDenied):
            self.preview(actor=self.owner)

    def test_late_audit_failure_rolls_back_source_and_order(self):
        from .models import MedicalAuditEvent
        original = MedicalAuditEvent.objects.create
        def fail_order(**kwargs):
            if kwargs.get("action") == "order_draft_created":
                raise DatabaseError("synthetic")
            return original(**kwargs)
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=fail_order):
            with self.assertRaises(MedicalAuditUnavailable):
                self.save()
        self.assertFalse(MedicalOrder.objects.exists())
        self.assertFalse(MedicalOrderRevision.objects.exists())

    def test_source_binding_tamper_is_not_readable(self):
        version, _ = self.save()
        version.source_version_id += 1
        with self.assertRaises(MedicalDataUnavailable):
            read_order_revision(version)

    def test_source_change_during_save_rolls_back(self):
        from .order_content import encrypt_order_revision
        def change_source(*args, **kwargs):
            type(self.business).objects.filter(pk=self.business.pk).update(name="Concurrent synthetic change")
            return encrypt_order_revision(*args, **kwargs)
        with patch("apps.medical.order_services.encrypt_order_revision", side_effect=change_source):
            with self.assertRaises(InvalidTransition):
                self.save()
        self.assertFalse(MedicalOrder.objects.exists())

    def test_preview_api_is_private_and_has_no_mutation(self):
        client = APIClient(); client.force_authenticate(self.doctor)
        response = client.get("/api/medical/orders/preview/", {"business_id": self.business.pk,
            "patient_id": self.patient.pk, "encounter_id": self.encounter_record.pk,
            "appointment_id": self.appointment.pk, "template_version_id": self.template.pk})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertFalse(MedicalOrder.objects.exists())
        saved = client.post("/api/medical/orders/", {"business_id": self.business.pk,
            "patient_id": self.patient.pk, "encounter_id": self.encounter_record.pk,
            "expected_patient_revision": response.data["patient_revision"],
            "expected_encounter_revision": response.data["encounter_revision"],
            "template_version_id": self.template.pk,
            "expected_source_digest": response.data["template_source"]["source_digest"],
            "content": {"kind": "other", "text": "Reviewed text", "medication": {}}},
            format="json", HTTP_IDEMPOTENCY_KEY="api-template")
        self.assertEqual(saved.status_code, 201, saved.data)
        version = MedicalOrderRevision.objects.get(pk=saved.data["version_id"])
        self.assertEqual(read_order_revision(version)["template_source"], response.data["template_source"])

    def test_unapproved_foreign_and_other_personal_template_are_denied(self):
        from apps.businesses.models import Business
        from .common_template_services import save_common_template_draft
        from .models import MedicalDocumentTemplate
        from .template_services import save_personal_template_draft
        draft, _ = save_common_template_draft(actor=self.head, business_id=self.business.pk,
            title="Unapproved", text="Synthetic", idempotency_key="unapproved")
        with self.assertRaises(PermissionDenied):
            self.preview(template_version_id=draft.pk)
        personal, _ = save_personal_template_draft(actor=self.head, business_id=self.business.pk,
            title="Other personal", text="Synthetic", idempotency_key="personal")
        fixtures.submit_personal_template(actor=self.head, business_id=self.business.pk,
            version_id=personal.pk, idempotency_key="personal-submit")
        fixtures.decide_template_review(actor=self.head, business_id=self.business.pk,
            version_id=personal.pk, decision="approved", reason="", idempotency_key="personal-approve")
        with self.assertRaises(PermissionDenied):
            self.preview(template_version_id=personal.pk)
        other = Business.objects.create(owner=self.owner, name="Other", slug="other-order-source")
        MedicalDocumentTemplate.objects.filter(pk=self.template.template_id).update(business=other)
        with self.assertRaises(PermissionDenied):
            self.preview()

    def test_own_approved_personal_template_is_available(self):
        from .template_services import save_personal_template_draft
        personal, _ = save_personal_template_draft(actor=self.doctor, business_id=self.business.pk,
            title="Own personal", text="Synthetic {{patient.full_name}}", idempotency_key="own")
        fixtures.submit_personal_template(actor=self.doctor, business_id=self.business.pk,
            version_id=personal.pk, idempotency_key="own-submit")
        fixtures.decide_template_review(actor=self.head, business_id=self.business.pk,
            version_id=personal.pk, decision="approved", reason="", idempotency_key="own-approve")
        preview = self.preview(template_version_id=personal.pk)
        self.assertNotIn("{{patient.full_name}}", preview["document_text"])
        version, _ = self.save(template_version_id=personal.pk,
            expected_source_digest=preview["template_source"]["source_digest"])
        self.assertEqual(version.template_version_id, personal.pk)

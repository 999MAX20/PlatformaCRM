from unittest.mock import patch
from django.test import TestCase,override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied,NotFound,ValidationError
from rest_framework.test import APIClient
from apps.businesses.models import RolePermission
from apps.core.domain_errors import InvalidTransition
from apps.ai_core.tests_speech import audio_bytes
from .tests_assistance import MedicalAssistanceTests
from .tests_patient_services import key
from .assistance import suggest_format,accept_format
from .speech_assistance import suggest_dictation
from .order_services import save_order_draft
from .models import MedicalOrderRevision

@override_settings(MEDICAL_DATA_KEYS={"test":key(7)},MEDICAL_DATA_ACTIVE_KEY_ID="test",MEDICAL_IDENTITY_INDEX_KEY=key(8))
class OrderAssistanceTests(TestCase):
    setUpTestData=classmethod(MedicalAssistanceTests.setUpTestData.__func__)
    def setUp(self):
        MedicalAssistanceTests.setUp(self)
        for action in ("view","create","update"):
            RolePermission.objects.get_or_create(business_role=self.assignment.business_role,resource="medical_prescriptions",action=action,defaults={"scope":"own","is_allowed":True})
        self.args.update(field="order_text",appointment_id=self.appointment.pk,expected_patient_revision=self.patient.revision)
    def create_order(self):
        version,_=save_order_draft(actor=self.doctor,business_id=self.business.pk,patient_id=self.patient.pk,encounter_id=self.encounter_record.pk,
            expected_encounter_revision=1,expected_patient_revision=self.patient.revision,content={"kind":"other","text":"Original order","medication":{}},idempotency_key="new-order")
        return version
    def test_new_order_preview_and_accept_dont_create_order(self):
        result=suggest_format(**self.args)
        self.assertEqual(accept_format(**self.args,suggestion=result["text"],receipt=result["receipt"])["text"],result["text"])
        self.assertFalse(MedicalOrderRevision.objects.exists())
        api=APIClient();api.force_authenticate(self.doctor)
        response=api.post("/api/medical/assistance/suggest/",{k:v for k,v in self.args.items() if k!="actor"},format="json")
        self.assertEqual(response.status_code,200,response.data)
    def test_prescription_permission_and_existing_author_are_required(self):
        version=self.create_order();args=self.args|{"order_id":version.order_id,"expected_order_revision":1}
        self.assertTrue(suggest_format(**args)["receipt"])
        for changes in ({"actor":self.owner},{"patient_id":999999},{"business_id":999999},{"order_id":999999}):
            with self.assertRaises((PermissionDenied,NotFound)):suggest_format(**(args|changes))
        RolePermission.objects.filter(business_role=self.assignment.business_role,resource="medical_prescriptions",action="update").delete()
        with self.assertRaises(PermissionDenied):suggest_format(**args)
    def test_missing_revision_stale_order_and_branch_deny_before_provider(self):
        version=self.create_order();args=self.args|{"order_id":version.order_id,"expected_order_revision":2}
        with self.assertRaises(InvalidTransition):suggest_format(**args)
        with self.assertRaises(InvalidTransition):suggest_format(**(self.args|{"expected_patient_revision":999}))
        with self.assertRaises(ValidationError):suggest_format(**(self.args|{"order_id":version.order_id}))
        self.assignment.branches.clear()
        with self.assertRaises(PermissionDenied):suggest_format(**self.args)
        from apps.businesses.models import Business
        from apps.clients.models import Client
        from .models import PatientProfile
        foreign=Business.objects.create(owner=self.owner,name="Foreign order assistance",slug="foreign-order-assistance")
        patient=PatientProfile.objects.create(business=foreign,client=Client.objects.create(business=foreign,full_name="Foreign synthetic patient"),created_by=self.owner)
        for change in ({"business_id":foreign.pk},{"patient_id":patient.pk}):
            with self.assertRaises((PermissionDenied,NotFound)):suggest_format(**(self.args|change))
        self.provider.generate_text.assert_not_called()
    def test_revision_changed_during_provider_drops_response(self):
        version=self.create_order();args=self.args|{"order_id":version.order_id,"expected_order_revision":1}
        response=self.provider.generate_text.return_value
        def update(*unused,**kwargs):
            save_order_draft(actor=self.doctor,business_id=self.business.pk,patient_id=self.patient.pk,encounter_id=self.encounter_record.pk,
                expected_encounter_revision=1,expected_patient_revision=self.patient.revision,order_id=version.order_id,expected_order_revision=1,
                content={"kind":"other","text":"Changed elsewhere","medication":{}},idempotency_key="change-order")
            return response
        self.provider.generate_text.side_effect=update
        with self.assertRaises(InvalidTransition):suggest_format(**args)
    def test_dictation_uses_same_prescription_scope_and_rechecks_revocation(self):
        policy={"provider":"synthetic","model":"synthetic","approval_reference":"isolated-only"}
        args=self.args|{"text":"","audio":audio_bytes(),"language":"ru"}
        with patch("apps.medical.speech_assistance.medical_speech_policy",return_value=policy),patch("apps.medical.speech_assistance.transcribe_medical_audio",return_value="Зуб 16 не болит"):
            result=suggest_dictation(**args)
            self.assertEqual(accept_format(**(self.args|{"text":""}),suggestion=result["text"],receipt=result["receipt"])["text"],result["text"])
            self.assignment.revoked_at=timezone.now();self.assignment.save(update_fields=["revoked_at"])
            with self.assertRaises(PermissionDenied):accept_format(**(self.args|{"text":""}),suggestion=result["text"],receipt=result["receipt"])
        self.assertFalse(MedicalOrderRevision.objects.exists())

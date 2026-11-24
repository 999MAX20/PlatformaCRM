from unittest import skipUnless
from django.db import connection
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from apps.businesses.models import RolePermission
from apps.core.domain_errors import InvalidTransition
from apps.procurement.models import PurchaseRequest
from . import tests_encounter_completion as fixtures
from .tests_order_concurrency import OrderConcurrencyTests
from .tests_patient_services import key
from .procurement_prompt import claim_prompt, record_prompt_decision, MedicalProcurementPrompt


@override_settings(MEDICAL_DATA_KEYS={"test":key(7)},MEDICAL_DATA_ACTIVE_KEY_ID="test",MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ProcurementPromptTests(TestCase):
    setUpTestData=classmethod(fixtures.EncounterCompletionTests.setUpTestData.__func__)
    complete=fixtures.EncounterCompletionTests.complete

    def setUp(self):
        fixtures.EncounterCompletionTests.setUp(self)
        RolePermission.objects.get_or_create(business_role=self.role,resource="medical_records",action="create",defaults={"scope":"own","is_allowed":True})
        self.scope=dict(actor=self.doctor,business_id=self.business.pk,encounter_id=self.encounter_record.pk)

    def test_only_successful_completion_claims_once_and_no_answer_creates_no_request(self):
        with self.assertRaises(PermissionDenied):claim_prompt(**self.scope)
        self.complete()
        first=claim_prompt(**self.scope);self.assertTrue(first["show"])
        self.assertEqual(set(first),{"show","token","branch"})
        self.assertFalse(claim_prompt(**self.scope)["show"])
        command=dict(actor=self.doctor,business_id=self.business.pk,token=first["token"])
        record_prompt_decision(**command,decision="ack")
        record_prompt_decision(**command,decision="no")
        record_prompt_decision(**command,decision="no")
        with self.assertRaises(InvalidTransition):record_prompt_decision(**command,decision="yes")
        self.assertFalse(PurchaseRequest.objects.exists())
        self.appointment.refresh_from_db();self.assertEqual(self.appointment.status,"completed")
        self.assertEqual(MedicalProcurementPrompt.objects.count(),1)

    def test_crash_after_claim_does_not_reissue_display(self):
        self.complete();claim_prompt(**self.scope)
        self.assertFalse(claim_prompt(**self.scope)["show"])
        event=MedicalProcurementPrompt.objects.get();self.assertIsNone(event.acknowledged_at)
        self.assertEqual(event.decision,"")

    def test_current_actor_tenant_branch_and_revocation(self):
        self.complete()
        for values in ({"actor":self.owner},{"business_id":999999},{"encounter_id":999999}):
            with self.assertRaises(PermissionDenied):claim_prompt(**(self.scope|values))
        self.assignment.branches.clear()
        with self.assertRaises(PermissionDenied):claim_prompt(**self.scope)
        self.assignment.branches.add(self.first)
        first=claim_prompt(**self.scope)
        self.assignment.revoked_at=timezone.now();self.assignment.save(update_fields=["revoked_at"])
        with self.assertRaises(PermissionDenied):record_prompt_decision(actor=self.doctor,business_id=self.business.pk,token=first["token"],decision="yes")
        self.assertFalse(PurchaseRequest.objects.exists())


@skipUnless(connection.vendor=="postgresql","Requires PostgreSQL row locks")
@override_settings(MEDICAL_DATA_KEYS={"test":key(7)},MEDICAL_DATA_ACTIVE_KEY_ID="test",MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ProcurementPromptConcurrencyTests(TransactionTestCase):
    parallel=OrderConcurrencyTests.parallel
    complete=fixtures.EncounterCompletionTests.complete
    def setUp(self):
        ProcurementPromptTests.setUpTestData.__func__(self)
        ProcurementPromptTests.setUp(self)
        self.complete()

    def test_two_devices_get_one_display(self):
        self.assertCountEqual(self.parallel([lambda:claim_prompt(**self.scope)["show"],lambda:claim_prompt(**self.scope)["show"]]),[True,False])
        self.assertEqual(MedicalProcurementPrompt.objects.count(),1)

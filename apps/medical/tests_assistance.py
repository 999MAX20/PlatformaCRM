from unittest.mock import Mock,patch
from django.test import TestCase,override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied,NotFound,ValidationError
from rest_framework.test import APIClient
from apps.ai_core.providers.base import AIProviderResponse,AIProviderError
from apps.core.domain_errors import InvalidTransition
from . import tests_encounter_services as fixtures
from .tests_patient_services import key
from .assistance import suggest_format,accept_format,MedicalAssistanceUnavailable
from .models import MedicalEncounterRevision


@override_settings(MEDICAL_DATA_KEYS={"test":key(7)},MEDICAL_DATA_ACTIVE_KEY_ID="test",MEDICAL_IDENTITY_INDEX_KEY=key(8))
class MedicalAssistanceTests(TestCase):
    setUpTestData=classmethod(fixtures.PrimaryEncounterDraftTests.setUpTestData.__func__)
    def setUp(self):
        fixtures.PrimaryEncounterDraftTests.setUp(self)
        self.policy={"approved":True,"business_ids":[self.business.pk],"approval_reference":"synthetic-policy-only",
            "processing_location":"synthetic-local-test","training":False,"retention_seconds":0,
            "provider":"openai","model":"synthetic","endpoint":"https://synthetic.example.test"}
        self.override=override_settings(MEDICAL_AI_POLICY=self.policy);self.override.enable();self.addCleanup(self.override.disable)
        self.provider=Mock(base_url=self.policy["endpoint"])
        self.provider.generate_text.return_value=AIProviderResponse(output_text="Зуб 16: боли нет. Доза 1,5 мг.",model="synthetic",provider="openai")
        self.provider_patch=patch("apps.medical.assistance.get_ai_provider",return_value=self.provider);self.provider_patch.start();self.addCleanup(self.provider_patch.stop)
        self.args=dict(actor=self.doctor,business_id=self.business.pk,patient_id=self.patient.pk,encounter_id=self.encounter_record.pk,
            expected_revision=1,field="complaints",text="Зуб 16 боли нет доза 1,5 мг")

    def test_bounded_field_preview_accept_never_writes_draft(self):
        result=suggest_format(**self.args)
        prompt=self.provider.generate_text.call_args.args[0]
        self.assertNotIn(str(self.patient.client.full_name),prompt)
        self.assertNotIn('patient_id',prompt);self.assertNotIn('business_id',prompt)
        self.assertEqual(accept_format(**self.args,suggestion=result["text"],receipt=result["receipt"])["text"],result["text"])
        self.assertEqual(MedicalEncounterRevision.objects.count(),1)
        self.encounter_record.refresh_from_db();self.assertEqual(self.encounter_record.revision,1)

    def test_missing_policy_does_not_call_provider_and_manual_form_unaffected(self):
        with override_settings(MEDICAL_AI_POLICY={}):
            with self.assertRaises(MedicalAssistanceUnavailable):suggest_format(**self.args)
        self.provider.generate_text.assert_not_called()

    def test_changed_numbers_negations_words_and_provider_failure_rejected(self):
        for text in ("Зуб 17 боли нет доза 1,5 мг","Зуб 16 боли доза 1,5 мг","Зуб 16 боли нет доза 15 мг","Зуб 16 боли нет доза 1,5 мг диагноз кариес"):
            self.provider.generate_text.return_value=AIProviderResponse(output_text=text,model="synthetic",provider="openai")
            with self.assertRaises(MedicalAssistanceUnavailable):suggest_format(**self.args)
        self.provider.generate_text.side_effect=AIProviderError("Synthetic sensitive detail")
        with self.assertRaises(MedicalAssistanceUnavailable) as caught:suggest_format(**self.args)
        self.assertNotIn("sensitive",str(caught.exception))

    def test_role_tenant_patient_and_stale_before_provider(self):
        for changes in ({"actor":self.owner},{"business_id":999999},{"patient_id":999999},{"encounter_id":999999}):
            with self.assertRaises((PermissionDenied,NotFound)):suggest_format(**(self.args|changes))
        with self.assertRaises(InvalidTransition):suggest_format(**(self.args|{"expected_revision":2}))
        self.provider.generate_text.assert_not_called()

    def test_revoke_during_provider_drops_response(self):
        def revoke(*args,**kwargs):
            self.assignment.revoked_at=timezone.now();self.assignment.save(update_fields=["revoked_at"])
            return AIProviderResponse(output_text=self.args["text"],model="synthetic",provider="openai")
        self.provider.generate_text.side_effect=revoke
        with self.assertRaises(PermissionDenied):suggest_format(**self.args)

    def test_accept_binds_actor_field_revision_text_and_policy(self):
        result=suggest_format(**self.args)
        for changes in ({"field":"diagnosis"},{"text":"Changed clinical input"},{"suggestion":"Changed output"},{"receipt":result["receipt"]+"x"}):
            with self.assertRaises(InvalidTransition):accept_format(**(self.args|dict(suggestion=result["text"],receipt=result["receipt"])|changes))
        with override_settings(MEDICAL_AI_POLICY=self.policy|{"approval_reference":"different"}):
            with self.assertRaises(InvalidTransition):accept_format(**self.args,suggestion=result["text"],receipt=result["receipt"])

    def test_http_private_and_no_data(self):
        api=APIClient();api.force_authenticate(self.doctor);data={k:v for k,v in self.args.items() if k!="actor"}
        response=api.post("/api/medical/assistance/suggest/",data,format="json")
        self.assertEqual(response.status_code,200,response.data);self.assertEqual(response["Cache-Control"],"no-store, private")
        self.assertEqual(api.post("/api/medical/assistance/suggest/",data|{"text":""},format="json").status_code,400)
        self.assertEqual(api.post("/api/medical/assistance/suggest/",data|{"history":"forged"},format="json").status_code,400)

    def test_numeric_sign_fraction_and_stale_provider_response(self):
        from .assistance import text_tokens
        for original,changed in [("-5 мг","5 мг"),("1/2 таблетки","1 2 таблетки"),("36-37","36 37"),("5%","5")]:
            self.assertNotEqual(text_tokens(original),text_tokens(changed))
        from .encounter_services import save_primary_encounter_draft
        def change(*args,**kwargs):
            save_primary_encounter_draft(actor=self.doctor,business_id=self.business.pk,patient_id=self.patient.pk,
                encounter_id=self.encounter_record.pk,expected_revision=1,content={"complaints":"Changed by another tab"},idempotency_key="other-tab")
            return AIProviderResponse(output_text=self.args["text"],model="synthetic",provider="openai")
        self.provider.generate_text.side_effect=change
        with self.assertRaises(InvalidTransition):suggest_format(**self.args)

    def test_receipt_expiry_and_explicit_no_fallback_router(self):
        import time
        result=suggest_format(**self.args)
        with patch("django.core.signing.time.time",return_value=time.time()+301):
            with self.assertRaises(InvalidTransition):accept_format(**self.args,suggestion=result["text"],receipt=result["receipt"])
        self.provider.generate_text.return_value=AIProviderResponse(output_text=self.args["text"],model="synthetic",provider="openrouter")
        with override_settings(MEDICAL_AI_POLICY=self.policy|{"provider":"openrouter","upstream_provider":"synthetic-approved"}):
            suggest_format(**self.args)
        options=self.provider.generate_text.call_args.args[0].provider_options
        self.assertEqual(options,{"allow_fallbacks":False,"only":["synthetic-approved"],"zdr":True,"data_collection":"deny"})

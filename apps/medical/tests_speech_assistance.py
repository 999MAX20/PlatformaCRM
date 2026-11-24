import io,json
from unittest.mock import patch
from django.test import TestCase,override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.exceptions import PermissionDenied,ValidationError
from apps.ai_core.tests_speech import audio_bytes
from apps.ai_core.providers import elevenlabs_speech
from apps.ai_core.providers.base import AIProviderError
from .tests_assistance import MedicalAssistanceTests
from .tests_patient_services import key
from .speech_assistance import suggest_dictation,transcribe_medical_audio
from .assistance import accept_format,MedicalAssistanceUnavailable


@override_settings(MEDICAL_DATA_KEYS={"test":key(7)},MEDICAL_DATA_ACTIVE_KEY_ID="test",MEDICAL_IDENTITY_INDEX_KEY=key(8))
class MedicalDictationTests(TestCase):
    setUpTestData=classmethod(MedicalAssistanceTests.setUpTestData.__func__)
    def setUp(self):
        MedicalAssistanceTests.setUp(self)
        self.speech_policy=self.policy|{"provider":"elevenlabs","model":elevenlabs_speech.DIAGNOSTIC_MODEL_ID,"endpoint":elevenlabs_speech.TRANSCRIPTION_URL}
        settings=override_settings(MEDICAL_SPEECH_POLICY=self.speech_policy);settings.enable();self.addCleanup(settings.disable)
        self.args.pop("text");self.args.update(text="",audio=audio_bytes(),language="kk")

    def test_audio_preview_accept_is_not_a_crm_command_or_saved_document(self):
        transcript="16 тіс ауырмайды. Бір бүтін бес миллиграмм."
        with patch("apps.medical.speech_assistance.transcribe_medical_audio",return_value=transcript) as provider:
            result=suggest_dictation(**self.args)
        self.assertEqual(provider.call_args.args,(self.args["audio"],"kk"))
        accepted=accept_format(**{k:v for k,v in self.args.items() if k not in ("audio","language")},suggestion=result["text"],receipt=result["receipt"])
        self.assertEqual(accepted["text"],transcript)
        self.encounter_record.refresh_from_db();self.assertEqual(self.encounter_record.revision,1)

    def test_policy_invalid_audio_and_late_revocation(self):
        with patch("apps.medical.speech_assistance.transcribe_medical_audio") as provider:
            with override_settings(MEDICAL_SPEECH_POLICY={}):
                with self.assertRaises(MedicalAssistanceUnavailable):suggest_dictation(**self.args)
            for audio in (b"",b"not-wave",b"x"*2_000_001):
                with self.assertRaises(ValidationError):suggest_dictation(**(self.args|{"audio":audio}))
            provider.assert_not_called()
        def revoke(*args):
            self.assignment.revoked_at=timezone.now();self.assignment.save(update_fields=["revoked_at"])
            return "Synthetic transcript"
        with patch("apps.medical.speech_assistance.transcribe_medical_audio",side_effect=revoke):
            with self.assertRaises(PermissionDenied):suggest_dictation(**self.args)

    def test_adapter_preserves_raw_number_words_and_sanitizes_failure(self):
        transcript="плюс семь семь ноль. Зуб шестнадцать не болит"
        with patch.object(elevenlabs_speech,"build_request",return_value="synthetic") as build,patch.object(elevenlabs_speech,"open_request",return_value=io.BytesIO(json.dumps({"text":transcript}).encode())):
            self.assertEqual(transcribe_medical_audio(audio_bytes(),"ru"),transcript)
            self.assertEqual(build.call_args.kwargs,{"keyterms":()})
        with patch.object(elevenlabs_speech,"build_request",side_effect=AIProviderError("private provider body")):
            with self.assertRaises(MedicalAssistanceUnavailable) as error:transcribe_medical_audio(audio_bytes(),"ru")
            self.assertNotIn("private",str(error.exception))

    def test_http_memory_upload_and_private_response(self):
        api=APIClient();api.force_authenticate(self.doctor)
        data={k:v for k,v in self.args.items() if k not in ("actor","audio")}
        with patch("apps.medical.speech_assistance.transcribe_medical_audio",return_value="Synthetic transcript"),patch("django.core.files.uploadhandler.TemporaryFileUploadHandler.new_file",side_effect=AssertionError("No audio files on disk")):
            response=api.post("/api/medical/assistance/dictation/",data|{"audio":SimpleUploadedFile("synthetic.wav",audio_bytes(),content_type="audio/wav")},format="multipart")
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(response["Cache-Control"],"no-store, private")
        self.assertEqual(api.post("/api/medical/assistance/dictation/",data|{"audio":SimpleUploadedFile("large.wav",b"x"*2_100_001)},format="multipart").status_code,400)

    def test_current_role_branch_and_foreign_patient_gate_audio_before_provider(self):
        from rest_framework.exceptions import NotFound
        from apps.businesses.models import Business
        from apps.clients.models import Client
        from .models import PatientProfile
        foreign=Business.objects.create(owner=self.owner,name="Foreign audio",slug="foreign-audio-test")
        patient=PatientProfile.objects.create(business=foreign,client=Client.objects.create(business=foreign,full_name="Synthetic foreign"),created_by=self.owner)
        with patch("apps.medical.speech_assistance.transcribe_medical_audio") as provider:
            for changes in ({"actor":self.owner},{"business_id":foreign.pk},{"patient_id":patient.pk}):
                with self.assertRaises((PermissionDenied,NotFound)):suggest_dictation(**(self.args|changes))
            self.assignment.branches.clear()
            with self.assertRaises(PermissionDenied):suggest_dictation(**self.args)
            provider.assert_not_called()

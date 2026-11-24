import json
from urllib import error
from django.conf import settings
from django.core import signing
from apps.ai_core.providers import elevenlabs_speech
from apps.ai_core.providers.base import AIProviderError
from apps.ai_core.speech import validate_audio, _transcript
from .assistance import _access, MedicalAssistanceUnavailable
from .identity_crypto import medical_request_digest


def medical_speech_policy(business_id):
    policy=getattr(settings,"MEDICAL_SPEECH_POLICY",{})
    if (not isinstance(policy,dict) or not isinstance(policy.get("business_ids"),list) or
        business_id not in policy["business_ids"] or policy.get("approved") is not True or
        not policy.get("approval_reference") or not policy.get("processing_location") or
        policy.get("training") is not False or policy.get("retention_seconds")!=0 or
        policy.get("provider")!="elevenlabs" or policy.get("model")!=elevenlabs_speech.DIAGNOSTIC_MODEL_ID or
        policy.get("endpoint")!=elevenlabs_speech.TRANSCRIPTION_URL):
        raise MedicalAssistanceUnavailable()
    return policy


def transcribe_medical_audio(content,language):
    try:
        call=elevenlabs_speech.build_request(content,language,keyterms=())
        with elevenlabs_speech.open_request(call,timeout=20) as response:
            raw=response.read(65537)
            if len(raw)>65536:
                raise AIProviderError()
            result=json.loads(raw)
        # Medical dictation must not run phone normalization or the CRM command planner.
        return _transcript(result,"/v1/speech-to-text")
    except (AIProviderError,error.URLError,OSError,ValueError,UnicodeError):
        raise MedicalAssistanceUnavailable() from None


def suggest_dictation(*,actor,business_id,patient_id,encounter_id,field,expected_revision,text,audio,language,participation_id=None):
    from rest_framework.exceptions import ValidationError
    if not isinstance(text,str) or len(text)>8000 or language not in ("ru","kk","auto"):
        raise ValidationError({"text":"Select the current field and language."})
    scope=dict(business_id=business_id,patient_id=patient_id,encounter_id=encounter_id,participation_id=participation_id)
    binding=_access(actor,scope,field,expected_revision)
    policy=medical_speech_policy(business_id)
    validate_audio(audio)
    transcript=transcribe_medical_audio(audio,language)
    _access(actor,scope,field,expected_revision)
    if medical_speech_policy(business_id)!=policy or not isinstance(transcript,str) or not transcript.strip() or len(transcript)>4000:
        raise MedicalAssistanceUnavailable()
    output=(text.rstrip()+"\n" if text.strip() else "")+transcript.strip()
    if len(output)>12000:
        raise MedicalAssistanceUnavailable()
    binding.update(mode="dictation",input_digest=medical_request_digest({"text":text},business_id=business_id),
        output_digest=medical_request_digest({"text":output},business_id=business_id),provider=policy["provider"],
        model=policy["model"],policy_digest=medical_request_digest(policy,business_id=business_id))
    return {"text":output,"receipt":signing.dumps(binding,salt="medical-assistance",compress=True),"field":field,"revision":expected_revision}

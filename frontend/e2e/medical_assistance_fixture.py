import json
from apps.ai_core.providers.base import AIProviderResponse
from apps.businesses.models import Business
from apps.medical import assistance


def install_synthetic_assistance():
    original=assistance.medical_ai_policy
    class SyntheticProvider:
        def generate_text(self,prompt,**kwargs):
            text=json.loads(prompt.rsplit("\n",1)[1])["text"]
            return AIProviderResponse(output_text=text.rstrip()+".",provider="openai",model="synthetic-local-format")
    def policy(business_id):
        if not Business.objects.filter(pk=business_id,name__startswith="Synthetic completion").exists():
            return original(business_id)
        return {"provider":"openai","model":"synthetic-local-format","approval_reference":"synthetic-isolated-test"},SyntheticProvider()
    assistance.medical_ai_policy=policy
    from apps.medical import speech_assistance
    original_speech=speech_assistance.medical_speech_policy
    def speech_policy(business_id):
        if not Business.objects.filter(pk=business_id,name__startswith="Synthetic completion").exists():
            return original_speech(business_id)
        return {"provider":"elevenlabs","model":"synthetic-local-speech","approval_reference":"synthetic-isolated-test"}
    speech_assistance.medical_speech_policy=speech_policy
    speech_assistance.transcribe_medical_audio=lambda content,language: "16 тіс ауырмайды" if language=="kk" else "Зуб 16 не болит"

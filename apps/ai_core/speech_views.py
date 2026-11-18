from django.core.files.uploadhandler import MemoryFileUploadHandler, StopUpload
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.ai_core.conversation_access import voice_access
from apps.ai_core.providers.base import AIProviderError
from apps.ai_core.speech import MAX_AUDIO_BYTES, MAX_AUDIO_SECONDS, transcribe_audio
from apps.ai_core.speech_configuration import speech_ready
from apps.ai_core.speech_formatting import format_transcript
from apps.core.permissions import accessible_businesses


class AudioUploadHandler(MemoryFileUploadHandler):
    def handle_raw_input(self, input_data, META, content_length, boundary, encoding=None):
        self.activated = True
        self.received = 0

    def receive_data_chunk(self, raw_data, start):
        self.received += len(raw_data)
        if self.received > MAX_AUDIO_BYTES:
            raise StopUpload(connection_reset=False)
        return super().receive_data_chunk(raw_data, start)


def speech_scope(user, business_id):
    business = get_object_or_404(accessible_businesses(user), pk=business_id)
    voice_access(business=business, user=user)
    return business


class SpeechInput(serializers.Serializer):
    business = serializers.IntegerField(min_value=1)
    language = serializers.ChoiceField(choices=["auto", "ru", "kk"], default="auto")
    format_text = serializers.BooleanField(default=True)
    audio = serializers.FileField(max_length=100, allow_empty_file=False)


class SpeechView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ai_assistant"
    parser_classes = [MultiPartParser]

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        return response

    def initialize_request(self, request, *args, **kwargs):
        # Audio exists only in bounded request memory, never in Django's temp uploader.
        request.upload_handlers = [AudioUploadHandler(request)]
        return super().initialize_request(request, *args, **kwargs)

    def get(self, request):
        business_id = serializers.IntegerField(min_value=1).run_validation(request.query_params.get("business"))
        business = speech_scope(request.user, business_id)
        return Response({"business": business.pk,
            "ready": speech_ready(),
            "max_seconds": MAX_AUDIO_SECONDS, "max_bytes": MAX_AUDIO_BYTES})

    def post(self, request):
        serializer = SpeechInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        speech_scope(request.user, values["business"])
        try:
            result = transcribe_audio(values["audio"].read(MAX_AUDIO_BYTES + 1), values["language"])
            if values["format_text"]:
                result["text"] = format_transcript(result["text"])
        except AIProviderError as exc:
            return Response({"code": exc.code, "retryable": exc.retryable}, status=503)
        finally:
            values["audio"].close()
        # A permission revoked during the provider call must not expose its result.
        speech_scope(request.user, values["business"])
        response = Response(result)
        response["Cache-Control"] = "no-store"
        return response

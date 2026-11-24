from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from django.core.files.uploadhandler import MemoryFileUploadHandler
from rest_framework.exceptions import ValidationError
from .serializers import StrictSerializer
from .assistance import suggest_format,accept_format


class SuggestionSerializer(StrictSerializer):
    business_id=serializers.IntegerField(min_value=1)
    patient_id=serializers.IntegerField(min_value=1)
    encounter_id=serializers.IntegerField(min_value=1)
    expected_revision=serializers.IntegerField(min_value=1)
    field=serializers.CharField(max_length=40)
    text=serializers.CharField(max_length=8000,trim_whitespace=False)
    participation_id=serializers.IntegerField(min_value=1,required=False,allow_null=True)


class AcceptSerializer(SuggestionSerializer):
    text=serializers.CharField(max_length=8000,allow_blank=True,trim_whitespace=False)
    suggestion=serializers.CharField(max_length=12000,trim_whitespace=False)
    receipt=serializers.CharField(max_length=4000)


class DictationSerializer(SuggestionSerializer):
    text=serializers.CharField(max_length=8000,allow_blank=True,trim_whitespace=False)
    audio=serializers.FileField()
    language=serializers.ChoiceField(choices=("ru","kk","auto"))


class MedicalAssistanceThrottle(UserRateThrottle):
    scope="medical_assistance"
    rate="12/min"


class MedicalAssistanceViewSet(viewsets.GenericViewSet):
    permission_classes=[IsAuthenticated]
    throttle_classes=[MedicalAssistanceThrottle]
    def get_serializer_class(self):
        return {"accept":AcceptSerializer,"dictation":DictationSerializer}.get(self.action,SuggestionSerializer)
    def finalize_response(self,request,response,*args,**kwargs):
        response=super().finalize_response(request,response,*args,**kwargs)
        response["Cache-Control"]="no-store, private"
        return response
    @action(detail=False,methods=["post"])
    def suggest(self,request):
        data=self.get_serializer(data=request.data);data.is_valid(raise_exception=True)
        return Response(suggest_format(actor=request.user,**data.validated_data))
    @action(detail=False,methods=["post"])
    def accept(self,request):
        data=self.get_serializer(data=request.data);data.is_valid(raise_exception=True)
        return Response(accept_format(actor=request.user,**data.validated_data))
    @action(detail=False,methods=["post"])
    def dictation(self,request):
        from .speech_assistance import suggest_dictation
        try:
            size=int(request.META.get("CONTENT_LENGTH",0))
        except (TypeError,ValueError):
            size=0
        if not 0<size<=2_100_000:
            raise ValidationError({"audio":"Audio exceeds the upload limit."})
        request._request.upload_handlers=[MemoryFileUploadHandler(request._request)]
        data=self.get_serializer(data=request.data);data.is_valid(raise_exception=True)
        payload=dict(data.validated_data);uploaded=payload.pop("audio")
        try:
            content=uploaded.read(2_000_001)
        finally:
            uploaded.close()
        return Response(suggest_dictation(actor=request.user,audio=content,**payload))

from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .record_services import open_dental_record
from .serializers import StrictSerializer


class RecordOpenSerializer(StrictSerializer):
    business_id = serializers.IntegerField(min_value=1)
    patient_id = serializers.IntegerField(min_value=1)
    number = serializers.CharField(max_length=64)
    expected_patient_revision = serializers.IntegerField(min_value=1)
    appointment_id = serializers.IntegerField(min_value=1, required=False)
    participation_id = serializers.IntegerField(min_value=1, required=False)


class MedicalRecordViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = RecordOpenSerializer
    http_method_names = ["post", "options"]

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store, private"
        response["Pragma"] = "no-cache"
        return response

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record, replayed = open_dental_record(actor=request.user, **serializer.validated_data,
            idempotency_key=request.headers.get("Idempotency-Key"))
        return Response({"id": record.pk, "patient_id": record.patient_id, "replayed": replayed},
                        status=200 if replayed else 201)

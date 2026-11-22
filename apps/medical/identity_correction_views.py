from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.core.domain_errors import ModuleDisabled
from .identity_correction_reads import list_identity_corrections
from .identity_iin_corrections import decide_iin_correction, request_iin_correction
from .patient_search import record_denied_patient_search
from .serializers import IdentityCorrectionDecisionSerializer, IdentityCorrectionListSerializer, PatientIINCorrectionSerializer


def _result(correction, replayed):
    return {"id": correction.pk, "patient_id": correction.patient_id, "state": correction.state,
            "applied_revision": correction.applied_revision, "replayed": replayed}


class PatientIdentityCorrectionsMixin:
    @action(detail=False, methods=["get"], url_path="identity-corrections")
    def identity_corrections(self, request):
        serializer = IdentityCorrectionListSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        try:
            result = list_identity_corrections(actor=request.user, **serializer.validated_data)
        except (PermissionDenied, ModuleDisabled):
            record_denied_patient_search(actor=request.user, business_id=serializer.validated_data["business_id"])
            raise
        return Response(result)

    @action(detail=True, methods=["post"], url_path="iin-correction")
    def iin_correction(self, request, pk=None):
        if request.query_params:
            raise ValidationError({"request": "Provide correction fields only in the request body."})
        serializer = PatientIINCorrectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            correction, replayed = request_iin_correction(actor=request.user, patient_id=int(pk),
                **serializer.validated_data, idempotency_key=request.headers.get("Idempotency-Key"))
        except (PermissionDenied, ModuleDisabled):
            record_denied_patient_search(actor=request.user, business_id=serializer.validated_data["business_id"])
            raise
        return Response(_result(correction, replayed), status=status.HTTP_200_OK if replayed else status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path=r"identity-corrections/(?P<correction_id>[0-9]+)/decision")
    def identity_correction_decision(self, request, correction_id=None):
        if request.query_params:
            raise ValidationError({"request": "Provide decision fields only in the request body."})
        serializer = IdentityCorrectionDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            correction, replayed = decide_iin_correction(actor=request.user, correction_id=int(correction_id),
                **serializer.validated_data, idempotency_key=request.headers.get("Idempotency-Key"))
        except (PermissionDenied, ModuleDisabled):
            record_denied_patient_search(actor=request.user, business_id=serializer.validated_data["business_id"])
            raise
        return Response(_result(correction, replayed))

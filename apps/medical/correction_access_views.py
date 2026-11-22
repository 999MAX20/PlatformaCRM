from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.domain_errors import ModuleDisabled
from .correction_access_context import observe_correction_access_expiry
from .correction_access_reads import (correction_access_payload, list_correction_access, list_correction_targets,
                                      read_correction_request, read_correction_target)
from .correction_access_services import close_correction_access, request_correction_access, review_correction_access
from .correction_access_writes import save_correction_target
from .patient_search import record_denied_patient_search
from .serializers import StrictSerializer


class CorrectionScopeSerializer(StrictSerializer):
    business_id = serializers.IntegerField(min_value=1)


class CorrectionReadSerializer(CorrectionScopeSerializer):
    head = serializers.BooleanField(default=False)


class CorrectionTargetReadSerializer(CorrectionScopeSerializer):
    version_id = serializers.IntegerField(min_value=1, required=False)


class CorrectionListSerializer(CorrectionReadSerializer):
    branch_id = serializers.IntegerField(min_value=1)
    client_id = serializers.IntegerField(min_value=1)
    before_id = serializers.IntegerField(min_value=1, required=False)
    limit = serializers.IntegerField(min_value=1, max_value=50, default=25)


class CorrectionTargetsSerializer(CorrectionScopeSerializer):
    branch_id = serializers.IntegerField(min_value=1)
    client_id = serializers.IntegerField(min_value=1)
    before_id = serializers.IntegerField(min_value=1, required=False)
    limit = serializers.IntegerField(min_value=1, max_value=50, default=25)


class CorrectionRequestSerializer(CorrectionScopeSerializer):
    encounter_id = serializers.IntegerField(min_value=1)
    document_id = serializers.IntegerField(min_value=1, required=False)
    expected_patient_revision = serializers.IntegerField(min_value=1)
    expected_target_revision = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(max_length=2000, allow_blank=False)


class CorrectionReviewSerializer(CorrectionScopeSerializer):
    expected_revision = serializers.IntegerField(min_value=1)
    decision = serializers.ChoiceField(choices=("approve", "reject"))
    reason = serializers.CharField(max_length=2000, allow_blank=False)


class CorrectionCloseSerializer(CorrectionReviewSerializer):
    decision = serializers.ChoiceField(choices=("withdraw", "complete", "revoke"))


class CorrectionSaveSerializer(CorrectionScopeSerializer):
    expected_revision = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(max_length=2000, allow_blank=False)
    content = serializers.DictField(required=False)
    document_text = serializers.CharField(max_length=131072, allow_blank=True, trim_whitespace=False, required=False)


class CorrectionAccessViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CorrectionScopeSerializer
    lookup_value_regex = r"[0-9]+"
    http_method_names = ["get", "post", "head", "options"]

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store, private"
        response["Pragma"] = "no-cache"
        return response

    def _call(self, request, serializer_class, service, *, request_id=None, command=False):
        if command and request.query_params:
            raise ValidationError({"request": "Provide command fields only in the request body."})
        serializer = serializer_class(data=request.data if command else request.query_params)
        serializer.is_valid(raise_exception=True)
        values = dict(serializer.validated_data)
        if request_id is not None:
            values["request_id"] = int(request_id)
        if command:
            values["idempotency_key"] = request.headers.get("Idempotency-Key")
        try:
            if service in {read_correction_target, save_correction_target}:
                observe_correction_access_expiry(actor=request.user, business_id=values["business_id"],
                                                  request_id=values["request_id"])
            result = service(actor=request.user, **values)
        except (PermissionDenied, ModuleDisabled):
            record_denied_patient_search(actor=request.user, business_id=values["business_id"])
            raise
        if command:
            item, replayed = result
            if service == save_correction_target:
                return Response({"version_id": item.pk, "revision": item.revision, "replayed": replayed})
            return Response({**correction_access_payload(item), "replayed": replayed},
                            status=201 if service == request_correction_access and not replayed else 200)
        return Response(result)

    def list(self, request):
        return self._call(request, CorrectionListSerializer, list_correction_access)

    def retrieve(self, request, pk=None):
        return self._call(request, CorrectionReadSerializer, read_correction_request, request_id=pk)

    def create(self, request):
        return self._call(request, CorrectionRequestSerializer, request_correction_access, command=True)

    @action(detail=False, methods=["get"])
    def targets(self, request):
        return self._call(request, CorrectionTargetsSerializer, list_correction_targets)

    @action(detail=True, methods=["get"])
    def target(self, request, pk=None):
        return self._call(request, CorrectionTargetReadSerializer, read_correction_target, request_id=pk)

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        return self._call(request, CorrectionReviewSerializer, review_correction_access, request_id=pk, command=True)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        return self._call(request, CorrectionCloseSerializer, close_correction_access, request_id=pk, command=True)

    @action(detail=True, methods=["post"], url_path="save-draft")
    def save_draft(self, request, pk=None):
        return self._call(request, CorrectionSaveSerializer, save_correction_target, request_id=pk, command=True)

from rest_framework.decorators import action
from rest_framework.response import Response

from .representative_selectors import list_patient_representatives, representation_verification_form
from .representative_serializers import (RepresentativeListSerializer, RepresentativeRevokeSerializer,
                                        RepresentativeVerifySerializer)
from .representative_services import verify_patient_representative, revoke_patient_representative
from .serializers import PatientScopeSerializer


class PatientRepresentativesMixin:
    @action(detail=False, methods=["get"], url_path="representative-form")
    def representative_form(self, request):
        serializer = PatientScopeSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(representation_verification_form(actor=request.user, **serializer.validated_data))

    @action(detail=True, methods=["get", "post"], url_path="representatives")
    def representatives(self, request, pk=None):
        if request.method == "GET":
            serializer = RepresentativeListSerializer(data=request.query_params)
            serializer.is_valid(raise_exception=True)
            return Response(list_patient_representatives(actor=request.user, patient_id=int(pk), **serializer.validated_data))
        serializer = RepresentativeVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        relation, replayed = verify_patient_representative(actor=request.user, patient_id=int(pk),
            **serializer.validated_data, idempotency_key=request.headers.get("Idempotency-Key"))
        return Response({"id": relation.pk, "revision": relation.revision, "replayed": replayed},
                        status=200 if replayed else 201)

    @action(detail=True, methods=["post"], url_path=r"representatives/(?P<representative_id>[0-9]+)/revoke")
    def revoke_representative(self, request, pk=None, representative_id=None):
        serializer = RepresentativeRevokeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        relation, replayed = revoke_patient_representative(actor=request.user, patient_id=int(pk),
            representative_id=int(representative_id), **serializer.validated_data,
            idempotency_key=request.headers.get("Idempotency-Key"))
        return Response({"id": relation.pk, "revision": relation.revision, "replayed": replayed})

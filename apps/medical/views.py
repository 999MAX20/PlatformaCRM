from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .identity_corrections import correct_patient_administrative_identity
from .identity_verification import verify_patient_identity
from .patient_selectors import (patient_administration_access, patient_verification_form,
                                read_patient_administration, reception_context)
from .patient_services import create_patient_profile, update_unverified_patient_profile
from .representative_views import PatientRepresentativesMixin
from .serializers import (PatientCorrectionSerializer, PatientCreateSerializer, PatientPreliminarySerializer,
                          PatientScopeSerializer, PatientVerifySerializer)


class PatientAdministrationViewSet(PatientRepresentativesMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    lookup_value_regex = r"[0-9]+"
    serializer_class = PatientScopeSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_serializer_class(self):
        return {"create": PatientCreateSerializer, "preliminary": PatientPreliminarySerializer,
            "verify": PatientVerifySerializer, "correct": PatientCorrectionSerializer}.get(self.action, PatientScopeSerializer)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store, private"
        response["Pragma"] = "no-cache"
        return response

    def _read(self, request, **identity):
        serializer = PatientScopeSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(read_patient_administration(actor=request.user, **serializer.validated_data, **identity))

    def retrieve(self, request, pk=None):
        return self._read(request, patient_id=int(pk))

    @action(detail=False, methods=["get"], url_path="access")
    def administration_access(self, request):
        serializer = PatientScopeSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(patient_administration_access(actor=request.user, **serializer.validated_data))

    @action(detail=False, methods=["get"], url_path="verification-form")
    def verification_form(self, request):
        serializer = PatientScopeSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(patient_verification_form(actor=request.user, **serializer.validated_data))

    @action(detail=False, methods=["get"], url_path=r"by-client/(?P<client_id>[0-9]+)")
    def by_client(self, request, client_id=None):
        return self._read(request, client_id=int(client_id))

    def _command(self, request, service, permission, *, patient_id=None, created=False):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        reception_context(actor=request.user, business_id=values["business_id"], branch_id=values["branch_id"], action=permission)
        identity = {"patient_id": patient_id} if patient_id is not None else {}
        patient, replayed = service(actor=request.user, **values, **identity,
                                   idempotency_key=request.headers.get("Idempotency-Key"))
        return Response({"id": patient.pk, "client_id": patient.client_id, "revision": patient.revision,
            "identity_status": patient.identity_status, "replayed": replayed},
            status=status.HTTP_201_CREATED if created and not replayed else status.HTTP_200_OK)

    def create(self, request):
        return self._command(request, create_patient_profile, "create", created=True)

    @action(detail=True, methods=["post"])
    def preliminary(self, request, pk=None):
        return self._command(request, update_unverified_patient_profile, "update", patient_id=int(pk))

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        return self._command(request, verify_patient_identity, "approve", patient_id=int(pk))

    @action(detail=True, methods=["post"])
    def correct(self, request, pk=None):
        return self._command(request, correct_patient_administrative_identity, "update", patient_id=int(pk))

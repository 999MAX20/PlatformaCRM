from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.csrf import AuthCookieCsrfMixin
from .serializers import StrictSerializer
from .file_audit import record_denied_file_access
from .issuance_reads import issuance_workspace, issuance_by_client, grant_data
from .issuance_services import create_document_grant, transition_document_grant
from .issuance_portal import login_portal, logout_portal, portal_documents, portal_pdf


class IssuanceScopeSerializer(StrictSerializer):
    business_id = serializers.IntegerField(min_value=1)
    patient_id = serializers.IntegerField(min_value=1)
    branch_id = serializers.IntegerField(min_value=1)


class IssuanceReadSerializer(IssuanceScopeSerializer):
    encounter_id = serializers.IntegerField(min_value=1, required=False)
    before_id = serializers.IntegerField(min_value=1, required=False)
    before_grant_id = serializers.IntegerField(min_value=1, required=False)
    before_version_id = serializers.IntegerField(min_value=1, required=False)


class IssuanceClientSerializer(StrictSerializer):
    business_id = serializers.IntegerField(min_value=1)
    branch_id = serializers.IntegerField(min_value=1)
    client_id = serializers.IntegerField(min_value=1)


class IssuanceCreateSerializer(IssuanceScopeSerializer):
    encounter_id = serializers.IntegerField(min_value=1)
    version_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), min_length=1, max_length=20)
    personally_verified = serializers.BooleanField()
    verification_reason = serializers.CharField(max_length=2000)
    representative_id = serializers.IntegerField(min_value=1, required=False)
    replaces_id = serializers.IntegerField(min_value=1, required=False)


class IssuanceTransitionSerializer(IssuanceScopeSerializer):
    expected_revision = serializers.IntegerField(min_value=1)
    action = serializers.ChoiceField(choices=("activate", "revoke"))
    reason = serializers.CharField(max_length=2000, allow_blank=True, default="")


class PrivateResponseMixin:
    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store, private"
        response["Pragma"] = "no-cache"
        response["Referrer-Policy"] = "no-referrer"
        response["X-Content-Type-Options"] = "nosniff"
        return response


class MedicalDocumentGrantViewSet(PrivateResponseMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]
    lookup_value_regex = r"[0-9]+"

    def get_serializer_class(self):
        return {"create": IssuanceCreateSerializer, "transition": IssuanceTransitionSerializer,
            "by_client": IssuanceClientSerializer}.get(self.action, IssuanceReadSerializer)

    def _execute(self, request, service, **extra):
        serializer = self.get_serializer(data=request.query_params if request.method == "GET" else request.data)
        serializer.is_valid(raise_exception=True)
        try:
            return service(actor=request.user, **serializer.validated_data, **extra)
        except (PermissionDenied, NotFound):
            record_denied_file_access(actor=request.user, business_id=serializer.validated_data["business_id"])
            raise

    def list(self, request):
        return Response(self._execute(request, issuance_workspace))

    @action(detail=False, methods=["get"], url_path="by-client")
    def by_client(self, request):
        return Response(self._execute(request, issuance_by_client))

    def create(self, request):
        grant, code, replayed = self._execute(request, create_document_grant, idempotency_key=request.headers.get("Idempotency-Key"))
        return Response({"grant": grant_data(grant), "code": code, "replayed": replayed}, status=200 if replayed else 201)

    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        grant, replayed = self._execute(request, transition_document_grant, grant_id=int(pk), idempotency_key=request.headers.get("Idempotency-Key"))
        return Response({"grant": grant_data(grant), "replayed": replayed})


class PortalLoginSerializer(StrictSerializer):
    code = serializers.CharField(max_length=40, trim_whitespace=False, write_only=True)


class MedicalDocumentPortalView(PrivateResponseMixin, AuthCookieCsrfMixin, APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    cookie_name = "medical_document_session"

    def post(self, request, business_slug, public_id=None):
        if public_id is not None:
            raise NotFound()
        serializer = PortalLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token, expires = login_portal(business_slug=business_slug, code=serializer.validated_data["code"],
            address=request.META.get("REMOTE_ADDR", "unknown"))
        response = Response({"session_expires_at": expires})
        response.set_cookie(self.cookie_name, token, max_age=max(1, int((expires - timezone.now()).total_seconds())),
            httponly=True, secure=not settings.DEBUG, samesite="Strict", path=f"/api/medical/portal/{business_slug}/")
        return response

    def delete(self, request, business_slug, public_id=None):
        if public_id is not None:
            raise NotFound()
        logout_portal(business_slug=business_slug, token=request.COOKIES.get(self.cookie_name))
        response = Response(status=204)
        response.delete_cookie(self.cookie_name, path=f"/api/medical/portal/{business_slug}/", samesite="Strict")
        return response

    def get(self, request, business_slug, public_id=None):
        scope = dict(business_slug=business_slug, token=request.COOKIES.get(self.cookie_name))
        if public_id is None:
            return Response(portal_documents(**scope))
        download = request.query_params.get("download") == "1"
        response = HttpResponse(portal_pdf(**scope, public_id=public_id, download=download), content_type="application/pdf")
        response["Content-Disposition"] = f'{"attachment" if download else "inline"}; filename="document.pdf"'
        response["Content-Security-Policy"] = "default-src 'none'; sandbox"
        return response

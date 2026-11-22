from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .serializers import StrictSerializer
from .document_rendering import DOCUMENT_FIELDS
from .common_template_services import (
    common_template_workspace_access, list_approved_templates, list_common_template_drafts,
    list_common_template_versions, read_approved_template_version, read_common_template_version,
    save_common_template_draft, submit_common_template,
)
from .template_reviews import (
    decide_template_review, list_pending_template_reviews, read_submitted_template,
    submit_personal_template,
)
from .template_availability import list_managed_templates, list_template_availability, set_template_availability
from .template_services import (
    list_personal_template_drafts, list_personal_template_versions,
    personal_template_workspace_access,
    read_personal_template_version, save_personal_template_draft,
    template_service_options,
)


class TemplateScopeSerializer(StrictSerializer):
    business_id = serializers.IntegerField(min_value=1)


class TemplateMetadataSerializer(StrictSerializer):
    language = serializers.ChoiceField(choices=["", "ru", "kk", "en"])
    category = serializers.CharField(max_length=255, allow_blank=True, trim_whitespace=False)
    specialty = serializers.CharField(max_length=255, allow_blank=True, trim_whitespace=False)
    service_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), max_length=50)


class TemplateDraftSerializer(TemplateScopeSerializer):
    title = serializers.CharField(max_length=255, trim_whitespace=False)
    text = serializers.CharField(max_length=131072, allow_blank=True, trim_whitespace=False)
    reason = serializers.CharField(max_length=2000, allow_blank=True, required=False, trim_whitespace=False)
    metadata = TemplateMetadataSerializer(required=False)


class TemplateUpdateSerializer(TemplateDraftSerializer):
    expected_revision = serializers.IntegerField(min_value=1)


class TemplateListSerializer(TemplateScopeSerializer):
    before_id = serializers.IntegerField(min_value=1, required=False)
    limit = serializers.IntegerField(min_value=1, max_value=50, required=False, default=20)


class TemplateSearchSerializer(TemplateListSerializer):
    q = serializers.CharField(max_length=255, allow_blank=True, required=False, default="")
    language = serializers.ChoiceField(choices=["", "ru", "kk", "en"], required=False, default="")
    category = serializers.CharField(max_length=255, allow_blank=True, required=False, default="")
    specialty = serializers.CharField(max_length=255, allow_blank=True, required=False, default="")
    service_id = serializers.IntegerField(min_value=1, required=False)


class ApprovedTemplateSearchSerializer(TemplateSearchSerializer):
    scope = serializers.ChoiceField(choices=["all", "personal", "common"], required=False, default="all")


class ManagedTemplateSearchSerializer(TemplateSearchSerializer):
    activity = serializers.ChoiceField(choices=["all", "active", "inactive"], required=False, default="all")


class TemplateAvailabilitySerializer(TemplateScopeSerializer):
    is_active = serializers.BooleanField()
    expected_revision = serializers.IntegerField(min_value=0)
    reason = serializers.CharField(max_length=2000, trim_whitespace=False)


class TemplateHistorySerializer(TemplateScopeSerializer):
    before_revision = serializers.IntegerField(min_value=1, required=False)
    limit = serializers.IntegerField(min_value=1, max_value=50, required=False, default=20)


class TemplateServiceOptionsSerializer(TemplateListSerializer):
    q = serializers.CharField(max_length=255, allow_blank=True, required=False, default="")


class TemplateDecisionSerializer(TemplateScopeSerializer):
    decision = serializers.ChoiceField(choices=["approved", "rejected"])
    reason = serializers.CharField(max_length=2000, allow_blank=True, required=False,
                                   default="", trim_whitespace=False)


class MedicalDocumentTemplateViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    lookup_value_regex = r"[0-9]+"
    serializer_class = TemplateScopeSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_serializer_class(self):
        if self.action == "availability":
            return TemplateAvailabilitySerializer if self.request.method == "POST" else TemplateHistorySerializer
        if self.action == "common":
            return TemplateDraftSerializer if self.request.method == "POST" else TemplateSearchSerializer
        return {"create": TemplateDraftSerializer, "draft": TemplateUpdateSerializer,
                "service_options": TemplateServiceOptionsSerializer, "managed": ManagedTemplateSearchSerializer,
                "common_draft": TemplateUpdateSerializer, "approved": ApprovedTemplateSearchSerializer,
                "common_revisions": TemplateHistorySerializer,
                "list": TemplateSearchSerializer, "pending_reviews": TemplateListSerializer,
                "decide": TemplateDecisionSerializer, "revisions": TemplateHistorySerializer}.get(
                    self.action, TemplateScopeSerializer)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store, private"
        response["Pragma"] = "no-cache"
        return response

    def _command(self, request, template_id=None, service=save_personal_template_draft):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        version, replayed = service(actor=request.user,
            template_id=template_id, **serializer.validated_data,
            idempotency_key=request.headers.get("Idempotency-Key"))
        return Response({"id": version.template_id, "version_id": version.pk,
                         "revision": version.revision, "replayed": replayed},
                        status=201 if template_id is None and not replayed else 200)

    def create(self, request):
        return self._command(request)

    @action(detail=False, methods=["get"], url_path="workspace-access")
    def workspace_access(self, request):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(personal_template_workspace_access(actor=request.user,
            **serializer.validated_data))

    @action(detail=False, methods=["get"], url_path="field-options")
    def field_options(self, request):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        personal_template_workspace_access(actor=request.user, **serializer.validated_data)
        return Response({"fields": DOCUMENT_FIELDS})

    @action(detail=False, methods=["get"], url_path="service-options")
    def service_options(self, request):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(template_service_options(actor=request.user, **serializer.validated_data))

    def list(self, request):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(list_personal_template_drafts(actor=request.user, **serializer.validated_data))

    @action(detail=False, methods=["get"])
    def managed(self, request):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(list_managed_templates(actor=request.user, **serializer.validated_data))

    @action(detail=True, methods=["get", "post"])
    def availability(self, request, pk=None):
        serializer = self.get_serializer(data=request.data if request.method == "POST" else request.query_params)
        serializer.is_valid(raise_exception=True)
        if request.method == "POST":
            change, replayed = set_template_availability(actor=request.user, template_id=int(pk),
                **serializer.validated_data, idempotency_key=request.headers.get("Idempotency-Key"))
            return Response({"id": change.template_id, "revision": change.revision,
                             "is_active": change.is_active, "replayed": replayed})
        return Response(list_template_availability(actor=request.user, template_id=int(pk), **serializer.validated_data))

    @action(detail=True, methods=["post"])
    def draft(self, request, pk=None):
        return self._command(request, template_id=int(pk))

    @action(detail=True, methods=["get"])
    def revisions(self, request, pk=None):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(list_personal_template_versions(actor=request.user,
            template_id=int(pk), **serializer.validated_data))

    @action(detail=False, methods=["get"], url_path=r"versions/(?P<version_id>[0-9]+)")
    def version(self, request, version_id=None):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(read_personal_template_version(actor=request.user,
            version_id=int(version_id), **serializer.validated_data))

    @action(detail=False, methods=["get"], url_path="pending-reviews")
    def pending_reviews(self, request):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(list_pending_template_reviews(actor=request.user, **serializer.validated_data))

    @action(detail=False, methods=["get"], url_path=r"versions/(?P<version_id>[0-9]+)/review")
    def review(self, request, version_id=None):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(read_submitted_template(actor=request.user,
            version_id=int(version_id), **serializer.validated_data))

    def _review_command(self, request, version_id, service):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review, replayed = service(actor=request.user, version_id=int(version_id),
            idempotency_key=request.headers.get("Idempotency-Key"), **serializer.validated_data)
        return Response({"review_id": review.pk, "version_id": review.version_id, "replayed": replayed})

    @action(detail=False, methods=["post"], url_path=r"versions/(?P<version_id>[0-9]+)/submit")
    def submit(self, request, version_id=None):
        return self._review_command(request, version_id, submit_personal_template)

    @action(detail=False, methods=["post"], url_path=r"versions/(?P<version_id>[0-9]+)/decision")
    def decide(self, request, version_id=None):
        return self._review_command(request, version_id, decide_template_review)

    def _read(self, request, service, **identifiers):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(service(actor=request.user, **identifiers, **serializer.validated_data))

    @action(detail=False, methods=["get", "post"], url_path="common")
    def common(self, request):
        if request.method == "POST":
            return self._command(request, service=save_common_template_draft)
        return self._read(request, list_common_template_drafts)

    @action(detail=False, methods=["get"], url_path="common/workspace-access")
    def common_access(self, request):
        return self._read(request, common_template_workspace_access)

    @action(detail=False, methods=["post"], url_path=r"common/(?P<template_id>[0-9]+)/draft")
    def common_draft(self, request, template_id=None):
        return self._command(request, template_id=int(template_id), service=save_common_template_draft)

    @action(detail=False, methods=["get"], url_path=r"common/(?P<template_id>[0-9]+)/revisions")
    def common_revisions(self, request, template_id=None):
        return self._read(request, list_common_template_versions, template_id=int(template_id))

    @action(detail=False, methods=["get"], url_path=r"common/versions/(?P<version_id>[0-9]+)")
    def common_version(self, request, version_id=None):
        return self._read(request, read_common_template_version, version_id=int(version_id))

    @action(detail=False, methods=["post"], url_path=r"common/versions/(?P<version_id>[0-9]+)/submit")
    def common_submit(self, request, version_id=None):
        return self._review_command(request, version_id, submit_common_template)

    @action(detail=False, methods=["get"], url_path="approved")
    def approved(self, request):
        return self._read(request, list_approved_templates)

    @action(detail=False, methods=["get"], url_path=r"approved/versions/(?P<version_id>[0-9]+)")
    def approved_version(self, request, version_id=None):
        return self._read(request, read_approved_template_version, version_id=int(version_id))

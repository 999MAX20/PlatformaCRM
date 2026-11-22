from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .serializers import StrictSerializer
from .template_reviews import (
    decide_template_review, list_pending_template_reviews, read_submitted_template,
    submit_personal_template,
)
from .template_services import (
    list_personal_template_drafts, list_personal_template_versions,
    personal_template_workspace_access,
    read_personal_template_version, save_personal_template_draft,
)


class TemplateScopeSerializer(StrictSerializer):
    business_id = serializers.IntegerField(min_value=1)


class TemplateDraftSerializer(TemplateScopeSerializer):
    title = serializers.CharField(max_length=255, trim_whitespace=False)
    text = serializers.CharField(max_length=131072, allow_blank=True, trim_whitespace=False)
    reason = serializers.CharField(max_length=2000, allow_blank=True, required=False, trim_whitespace=False)


class TemplateUpdateSerializer(TemplateDraftSerializer):
    expected_revision = serializers.IntegerField(min_value=1)


class TemplateListSerializer(TemplateScopeSerializer):
    before_id = serializers.IntegerField(min_value=1, required=False)
    limit = serializers.IntegerField(min_value=1, max_value=50, required=False, default=20)


class TemplateHistorySerializer(TemplateScopeSerializer):
    before_revision = serializers.IntegerField(min_value=1, required=False)
    limit = serializers.IntegerField(min_value=1, max_value=50, required=False, default=20)


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
        return {"create": TemplateDraftSerializer, "draft": TemplateUpdateSerializer,
                "list": TemplateListSerializer, "pending_reviews": TemplateListSerializer,
                "decide": TemplateDecisionSerializer, "revisions": TemplateHistorySerializer}.get(
                    self.action, TemplateScopeSerializer)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store, private"
        response["Pragma"] = "no-cache"
        return response

    def _command(self, request, template_id=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        version, replayed = save_personal_template_draft(actor=request.user,
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

    def list(self, request):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(list_personal_template_drafts(actor=request.user, **serializer.validated_data))

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

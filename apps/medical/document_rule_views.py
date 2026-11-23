from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .document_rule_content import MOMENTS, REVIEWERS, SIGNERS
from .document_rule_selectors import document_rule_access, document_rule_history, list_document_rules
from .document_rule_services import read_document_rules, save_document_rules
from .serializers import StrictSerializer


class RuleScopeSerializer(StrictSerializer):
    business_id = serializers.IntegerField(min_value=1)


class RulePageSerializer(RuleScopeSerializer):
    before_id = serializers.IntegerField(min_value=1, required=False)
    limit = serializers.IntegerField(min_value=1, max_value=50, default=20)


class RuleSearchSerializer(RulePageSerializer):
    q = serializers.CharField(max_length=255, required=False, default="", allow_blank=True)


class RuleRequirementsSerializer(StrictSerializer):
    required_at = serializers.ChoiceField(choices=MOMENTS)
    required_fields = serializers.ListField(child=serializers.CharField(max_length=128), max_length=100)
    reviewers = serializers.ListField(child=serializers.ChoiceField(choices=REVIEWERS), max_length=2)
    signers = serializers.ListField(child=serializers.ChoiceField(choices=SIGNERS), max_length=3)
    issuable = serializers.BooleanField()


class ServiceRuleSerializer(StrictSerializer):
    service_id = serializers.IntegerField(min_value=1)
    rule = RuleRequirementsSerializer()


class RuleContentSerializer(StrictSerializer):
    name = serializers.CharField(max_length=255)
    docx_allowed = serializers.BooleanField(default=False)
    default = RuleRequirementsSerializer()
    services = ServiceRuleSerializer(many=True)


class RuleSaveSerializer(RuleScopeSerializer):
    content = RuleContentSerializer()
    template_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), max_length=100)
    reason = serializers.CharField(max_length=2000)


class RuleUpdateSerializer(RuleSaveSerializer):
    expected_revision = serializers.IntegerField(min_value=1)


class MedicalDocumentKindViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]
    lookup_value_regex = r"[0-9]+"
    serializer_class = RuleScopeSerializer

    def get_serializer_class(self):
        return {"list": RuleSearchSerializer, "create": RuleSaveSerializer,
            "save": RuleUpdateSerializer, "history": RulePageSerializer}.get(self.action, RuleScopeSerializer)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store, private"
        response["Pragma"] = "no-cache"
        return response

    def _read(self, request, service, **extra):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(service(actor=request.user, **serializer.validated_data, **extra))

    def list(self, request):
        return self._read(request, list_document_rules)

    @action(detail=False, methods=["get"], url_path="workspace-access")
    def workspace_access(self, request):
        return self._read(request, document_rule_access)

    @action(detail=False, methods=["get"], url_path=r"versions/(?P<version_id>[0-9]+)")
    def version(self, request, version_id=None):
        return self._read(request, read_document_rules, version_id=int(version_id))

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        return self._read(request, document_rule_history, kind_id=int(pk))

    def _save(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        version, replayed = save_document_rules(actor=request.user, **serializer.validated_data,
            kind_id=int(pk) if pk else None, idempotency_key=request.headers.get("Idempotency-Key"))
        return Response({"kind_id": version.kind_id, "version_id": version.pk,
            "revision": version.revision, "replayed": replayed}, status=201 if pk is None and not replayed else 200)

    def create(self, request):
        return self._save(request)

    @action(detail=True, methods=["post"])
    def save(self, request, pk=None):
        return self._save(request, pk)

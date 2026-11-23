from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .order_reads import list_orders, list_order_versions, order_workspace_access
from .order_services import read_order_version, save_order_draft
from .serializers import StrictSerializer


class OrderScopeSerializer(StrictSerializer):
    business_id = serializers.IntegerField(min_value=1)
    patient_id = serializers.IntegerField(min_value=1)


class OrderReadSerializer(OrderScopeSerializer):
    appointment_id = serializers.IntegerField(min_value=1, required=False)
    participation_id = serializers.IntegerField(min_value=1, required=False)


class OrderAccessSerializer(OrderReadSerializer):
    encounter_id = serializers.IntegerField(min_value=1)


class OrderListSerializer(OrderAccessSerializer):
    before_id = serializers.IntegerField(min_value=1, required=False)
    limit = serializers.IntegerField(min_value=1, max_value=50, required=False, default=20)


class OrderHistorySerializer(OrderReadSerializer):
    before_revision = serializers.IntegerField(min_value=1, required=False)
    limit = serializers.IntegerField(min_value=1, max_value=50, required=False, default=20)


class OrderDraftSerializer(OrderScopeSerializer):
    encounter_id = serializers.IntegerField(min_value=1)
    expected_encounter_revision = serializers.IntegerField(min_value=1)
    expected_patient_revision = serializers.IntegerField(min_value=1)
    content = serializers.JSONField()
    reason = serializers.CharField(max_length=2000, allow_blank=True, required=False, trim_whitespace=False)
    participation_id = serializers.IntegerField(min_value=1, required=False)


class OrderUpdateSerializer(OrderDraftSerializer):
    expected_order_revision = serializers.IntegerField(min_value=1)


class MedicalOrderViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    lookup_value_regex = r"[0-9]+"
    serializer_class = OrderReadSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_serializer_class(self):
        return {"create": OrderDraftSerializer, "draft": OrderUpdateSerializer,
                "list": OrderListSerializer, "revisions": OrderHistorySerializer,
                "workspace_access": OrderAccessSerializer}.get(self.action, OrderReadSerializer)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store, private"
        response["Pragma"] = "no-cache"
        return response

    def _read(self, request, service, **identity):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(service(actor=request.user, **identity, **serializer.validated_data))

    def _command(self, request, order_id=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        version, replayed = save_order_draft(actor=request.user, order_id=order_id,
            **serializer.validated_data, idempotency_key=request.headers.get("Idempotency-Key"))
        return Response({"id": version.order_id, "version_id": version.pk,
                         "revision": version.revision, "replayed": replayed},
                        status=201 if order_id is None and not replayed else 200)

    def create(self, request):
        return self._command(request)

    def list(self, request):
        return self._read(request, list_orders)

    @action(detail=False, methods=["get"], url_path="workspace-access")
    def workspace_access(self, request):
        return self._read(request, order_workspace_access)

    @action(detail=True, methods=["post"])
    def draft(self, request, pk=None):
        return self._command(request, order_id=int(pk))

    @action(detail=True, methods=["get"])
    def revisions(self, request, pk=None):
        return self._read(request, list_order_versions, order_id=int(pk))

    @action(detail=False, methods=["get"], url_path=r"versions/(?P<version_id>[0-9]+)")
    def version(self, request, version_id=None):
        return self._read(request, read_order_version, version_id=int(version_id))

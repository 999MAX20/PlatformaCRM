from decimal import Decimal
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from . import services


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if set(data) - set(self.fields):
            raise serializers.ValidationError({"fields": "Unknown fields are not allowed."})
        return super().to_internal_value(data)


class ScopeSerializer(StrictSerializer):
    business_id = serializers.IntegerField(min_value=1)
    branch_id = serializers.IntegerField(min_value=1)


class ContextSerializer(StrictSerializer):
    business_id = serializers.IntegerField(min_value=1)


class PageSerializer(ScopeSerializer):
    after_id = serializers.IntegerField(min_value=0, default=0)


class FieldsSerializer(StrictSerializer):
    material = serializers.CharField(max_length=200)
    specification = serializers.CharField(max_length=200, allow_blank=True)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0.001"))
    unit = serializers.ChoiceField(choices=services.UNITS)
    urgent = serializers.BooleanField()
    needed_by = serializers.DateField(allow_null=True)
    comment = serializers.CharField(max_length=1000, allow_blank=True)


class CreateSerializer(ScopeSerializer):
    fields = FieldsSerializer()


class ChangeSerializer(ScopeSerializer):
    expected_revision = serializers.IntegerField(min_value=1)
    action = serializers.ChoiceField(choices=("edit", "cancel"))
    reason = serializers.CharField(max_length=1000)
    fields = FieldsSerializer(required=False)


class PurchaseRequestViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    def get_serializer_class(self):
        return {"create": CreateSerializer, "change": ChangeSerializer, "context": ContextSerializer}.get(self.action, PageSerializer)

    @action(detail=False, methods=["get"])
    def context(self, request):
        serializer = self.get_serializer(data=request.query_params); serializer.is_valid(raise_exception=True)
        return Response(services.request_context(actor=request.user, **serializer.validated_data))

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store, private"
        return response

    def list(self, request):
        serializer = self.get_serializer(data=request.query_params); serializer.is_valid(raise_exception=True)
        return Response(services.list_own_requests(actor=request.user, **serializer.validated_data))

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        serializer = self.get_serializer(data=request.query_params); serializer.is_valid(raise_exception=True)
        return Response(services.own_history(actor=request.user, request_id=int(pk), **serializer.validated_data))

    def create(self, request):
        serializer = self.get_serializer(data=request.data); serializer.is_valid(raise_exception=True)
        item, replayed = services.create_request(actor=request.user, idempotency_key=request.headers.get("Idempotency-Key"), **serializer.validated_data)
        return Response(services.projection(item) | {"replayed": replayed})

    @action(detail=True, methods=["post"])
    def change(self, request, pk=None):
        serializer = self.get_serializer(data=request.data); serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data); data.setdefault("fields", {})
        item, replayed = services.change_own_request(actor=request.user, request_id=int(pk),
            idempotency_key=request.headers.get("Idempotency-Key"), **data)
        return Response(services.projection(item) | {"replayed": replayed})

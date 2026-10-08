from django.db import transaction
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.fields import IntegerField

from apps.businesses.models import Business
from apps.businesses.access import Actions, Resources, assert_can
from apps.core.audit import write_audit_log
from apps.core.crm_read_scope import scope_entity_history
from apps.core.custom_fields import (
    assert_custom_field_editable, custom_field_entity_access, custom_field_role_allowed,
    validate_custom_field_value,
)
from apps.core.models import AuditLog, CustomFieldDefinition, CustomFieldValue
from apps.core.permissions import user_can_access_business
from apps.core.serializers import BulkCustomFieldValueSerializer, CustomFieldDefinitionSerializer, CustomFieldValueSerializer
from apps.core.viewsets import TenantModelViewSet


class CustomFieldDefinitionViewSet(TenantModelViewSet):
    queryset = CustomFieldDefinition.objects.select_related("business")
    serializer_class = CustomFieldDefinitionSerializer
    action_permission_map = {**TenantModelViewSet.action_permission_map, "create": Actions.UPDATE, "destroy": Actions.UPDATE}

    def get_object(self):
        instance = super().get_object()
        if self.action in {"update", "partial_update", "destroy"}:
            return CustomFieldDefinition.objects.select_for_update().get(pk=instance.pk)
        return instance

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        assert_can(request.user, instance.business, Resources.SETTINGS, Actions.UPDATE)
        if instance.values.exists():
            raise ValidationError({"definition": "This field has saved values. Deactivate it to retain history."})
        write_audit_log(request, AuditLog.Actions.DELETE, instance)
        instance.delete()
        return Response(status=204)

    def get_queryset(self):
        queryset = super().get_queryset()
        if "business" in self.request.query_params:
            queryset = queryset.filter(business_id=IntegerField(min_value=1).run_validation(self.request.query_params["business"]))
        entity_type = self.request.query_params.get("entity_type")
        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)
        allowed_ids = [
            definition.id
            for definition in queryset.select_related("business")
            if custom_field_role_allowed(definition, self.request.user, "view")
        ]
        queryset = queryset.filter(id__in=allowed_ids)
        return queryset


class CustomFieldValueViewSet(TenantModelViewSet):
    queryset = CustomFieldValue.objects.select_related("business", "definition")
    serializer_class = CustomFieldValueSerializer

    def get_queryset(self):
        queryset = scope_entity_history(super().get_queryset().filter(
            entity_type__in=CustomFieldDefinition.EntityTypes.values,
        ), actor=self.request.user)
        if "business" in self.request.query_params:
            queryset = queryset.filter(business_id=IntegerField(min_value=1).run_validation(self.request.query_params["business"]))
        entity_type = self.request.query_params.get("entity_type")
        entity_id = self.request.query_params.get("entity_id")
        definition = self.request.query_params.get("definition")
        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)
        if entity_id:
            queryset = queryset.filter(entity_id=str(entity_id))
        if definition:
            queryset = queryset.filter(definition_id=definition)
        allowed_ids = [
            value.id
            for value in queryset.select_related("business", "definition")
            if custom_field_role_allowed(value.definition, self.request.user, "view")
        ]
        queryset = queryset.filter(id__in=allowed_ids)
        return queryset

    def _validate_write(self, serializer):
        candidate = self._scope_candidate_from_serializer(serializer)
        definition = CustomFieldDefinition.objects.select_for_update().get(pk=candidate.definition_id)
        assert_custom_field_editable(definition, self.request.user)
        custom_field_entity_access(actor=self.request.user, business=candidate.business,
                                   entity_type=candidate.entity_type, entity_id=candidate.entity_id)
        if "value_json" in serializer.validated_data:
            serializer.validated_data["value_json"] = validate_custom_field_value(
                definition=definition, value_json=serializer.validated_data["value_json"],
            )

    @transaction.atomic
    def perform_create(self, serializer):
        self._validate_write(serializer)
        super().perform_create(serializer)

    @transaction.atomic
    def perform_update(self, serializer):
        self._validate_write(serializer)
        super().perform_update(serializer)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        assert_can(request.user, instance.business, Resources.SETTINGS, Actions.DELETE)
        definition = CustomFieldDefinition.objects.select_for_update().get(pk=instance.definition_id)
        assert_custom_field_editable(definition, request.user)
        custom_field_entity_access(actor=request.user, business=instance.business,
                                   entity_type=instance.entity_type, entity_id=instance.entity_id)
        write_audit_log(request, AuditLog.Actions.DELETE, instance)
        instance.delete()
        return Response(status=204)

    @action(detail=False, methods=["post"], url_path="bulk-upsert")
    @transaction.atomic
    def bulk_upsert(self, request):
        serializer = BulkCustomFieldValueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        business = Business.objects.filter(id=serializer.validated_data["business"]).first()
        if business is None or not user_can_access_business(request.user, business):
            raise PermissionDenied("Business is not available.")

        entity_type = serializer.validated_data["entity_type"]
        entity_id = serializer.validated_data["entity_id"]
        custom_field_entity_access(actor=request.user, business=business,
                                   entity_type=entity_type, entity_id=entity_id)
        # Share the definition lock with settings edits/deletion so validation and
        # persisted values cannot observe incompatible definitions concurrently.
        definition_ids = [item["definition"].id for item in serializer.validated_data["values"]]
        definitions = {row.id: row for row in CustomFieldDefinition.objects.select_for_update().filter(
            pk__in=definition_ids,
        ).order_by("pk")}
        if len(definitions) != len(set(definition_ids)):
            raise ValidationError({"definition": "Definition is no longer available."})
        saved = []
        for item in serializer.validated_data["values"]:
            definition = definitions[item["definition"].id]
            if definition.business_id != business.id or definition.entity_type != entity_type:
                raise ValidationError({"definition": "Definition does not belong to this business/entity."})
            assert_custom_field_editable(definition, request.user)
            value_json = validate_custom_field_value(
                definition=definition,
                value_json=item.get("value_json", {}),
            )
            value, created = CustomFieldValue.objects.update_or_create(
                business=business,
                definition=definition,
                entity_type=entity_type,
                entity_id=str(entity_id),
                defaults={"value_json": value_json},
            )
            write_audit_log(request, AuditLog.Actions.CREATE if created else AuditLog.Actions.UPDATE, value)
            saved.append(value)

        return Response(CustomFieldValueSerializer(saved, many=True).data)

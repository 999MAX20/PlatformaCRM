from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.core.audit import write_actor_audit_log
from apps.core.models import AuditLog, ImportWorkspace, ImportMappingProfile
from apps.core.permissions import accessible_businesses
from .drafts import add_source, assert_workspace_access, correct_source, create_workspace, invalidate_preview, lock_workspace, prepared_rows
from .schema import FIELDS, configure_source
from .uploads import upload_sources
from .engine import preview_workspace, confirm_workspace
from .report_access import visible_report
from .suggestions import suggest_mapping, suggest_type
from .profiles import save_profile, apply_profile
from .activation import activation_preview, activate_records


class VersionInput(serializers.Serializer):
    version = serializers.IntegerField(min_value=1)


class OperationInput(VersionInput):
    background = serializers.BooleanField(default=False)


class WorkspaceInput(serializers.Serializer):
    business = serializers.IntegerField(min_value=1)


class SourceEditInput(VersionInput):
    source_id = serializers.IntegerField(min_value=1)
    corrections = serializers.JSONField()
    excluded = serializers.ListField(child=serializers.IntegerField(min_value=1), max_length=5000)


class SourceConfigInput(VersionInput):
    source_id = serializers.IntegerField(min_value=1)
    entity_type = serializers.ChoiceField(choices=list(FIELDS))
    mapping = serializers.JSONField()
    fields = serializers.JSONField(default=list)
    columns = serializers.JSONField(default=list)
    resolutions = serializers.JSONField(default=dict)


class SourceCopyInput(VersionInput):
    source_id = serializers.IntegerField(min_value=1)
    entity_type = serializers.ChoiceField(choices=list(FIELDS))


class SourceSelectionInput(VersionInput):
    source_id = serializers.IntegerField(min_value=1)


class SourceSaveInput(SourceConfigInput):
    corrections = serializers.JSONField()
    excluded = serializers.ListField(child=serializers.IntegerField(min_value=1), max_length=5000)


class SaveProfileInput(VersionInput):
    source_id = serializers.IntegerField(min_value=1)
    name = serializers.CharField(max_length=128)


class ApplyProfileInput(VersionInput):
    source_id = serializers.IntegerField(min_value=1)
    profile_id = serializers.IntegerField(min_value=1)


class ActivationInput(serializers.Serializer):
    token = serializers.CharField(max_length=200000)
    ids = serializers.ListField(child=serializers.IntegerField(min_value=1), min_length=1, max_length=5000)
    confirmed = serializers.BooleanField()

    def validate_confirmed(self, value):
        if not value:
            raise serializers.ValidationError("Explicit confirmation is required.")
        return value


def source_payload(source):
    headers = list(source.rows_json[0]) if source.rows_json else []
    return {"id": source.pk, "filename": source.original_filename, "sheet_name": source.sheet_name, "profile_id": source.profile_id,
        "entity_type": source.entity_type, "total_rows": len(source.rows_json),
        "headers": list(source.rows_json[0]) if source.rows_json else [], "mapping": source.mapping_json,
        "fields": source.fields_json, "columns": source.columns_json, "resolutions": source.resolutions_json,
        "corrections": source.corrections_json, "excluded": source.excluded_json,
        "suggested_mapping": {kind: suggest_mapping(headers, kind) for kind in FIELDS},
        "suggested_types": {header: suggest_type([row[header] for row in source.rows_json]) for header in headers}}


def workspace_payload(workspace, *, detail=True, actor=None):
    result = {"id": workspace.pk, "business": workspace.business_id, "state": workspace.state,
        "version": workspace.version, "validated_version": workspace.validated_version,
        "created_at": workspace.created_at, "updated_at": workspace.updated_at,
        "operation": {key: value for key, value in workspace.operation_json.items() if key != "claim_token"}}
    if detail:
        result.update(sources=[source_payload(source) for source in workspace.sources.order_by("pk")],
            report=visible_report(workspace, workspace.report_json, actor or workspace.actor),
            result=visible_report(workspace, workspace.result_json, actor or workspace.actor), mapping_fields=FIELDS)
    return result


class ImportWorkspaceViewSet(GenericViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ImportWorkspace.objects.select_related("business")
    http_method_names = ["get", "post", "head", "options"]
    serializer_class = WorkspaceInput

    def get_queryset(self):
        return super().get_queryset().filter(actor=self.request.user,
            business__in=accessible_businesses(self.request.user))

    def get_object(self):
        workspace = super().get_object()
        assert_workspace_access(workspace, self.request.user)
        return workspace

    def list(self, request):
        business_id = serializers.IntegerField(min_value=1).run_validation(request.query_params.get("business"))
        business = get_object_or_404(accessible_businesses(request.user), pk=business_id)
        assert_workspace_access(ImportWorkspace(business=business, actor=request.user), request.user)
        page = serializers.IntegerField(min_value=1).run_validation(request.query_params.get("page", 1))
        queryset = self.get_queryset().filter(business=business)
        return Response({"count": queryset.count(), "results": [workspace_payload(item, detail=False)
            for item in queryset[(page - 1) * 20:page * 20]]})

    def retrieve(self, request, pk=None):
        return Response(workspace_payload(self.get_object()))

    def create(self, request):
        serializer = WorkspaceInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        business_id = serializer.validated_data["business"]
        business = get_object_or_404(accessible_businesses(request.user), pk=business_id)
        workspace = create_workspace(business=business, actor=request.user)
        return Response(workspace_payload(workspace), status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def upload(self, request, pk=None):
        workspace = self.get_object()
        version = VersionInput(data=request.data)
        version.is_valid(raise_exception=True)
        upload = serializers.FileField().run_validation(request.FILES.get("file"))
        entity_type = serializers.ChoiceField(choices=list(FIELDS)).run_validation(request.data.get("entity_type", "clients"))
        workspace, _ = upload_sources(workspace_id=workspace.pk, actor=request.user,
            version=version.validated_data["version"], upload=upload, entity_type=entity_type)
        return Response(workspace_payload(workspace))

    @action(detail=True, methods=["post"])
    def configure(self, request, pk=None):
        workspace = self.get_object()
        serializer = SourceConfigInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        workspace, _ = configure_source(workspace_id=workspace.pk, actor=request.user, **serializer.validated_data)
        return Response(workspace_payload(workspace))

    @action(detail=True, methods=["post"])
    def correct(self, request, pk=None):
        workspace = self.get_object()
        serializer = SourceEditInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        workspace, _ = correct_source(workspace_id=workspace.pk, actor=request.user, **serializer.validated_data)
        return Response(workspace_payload(workspace))

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def save_source(self, request, pk=None):
        workspace = self.get_object()
        serializer = SourceSaveInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        corrections, excluded = data.pop("corrections"), data.pop("excluded")
        workspace, source = configure_source(workspace_id=workspace.pk, actor=request.user, **data)
        workspace, _ = correct_source(workspace_id=workspace.pk, actor=request.user,
            source_id=source.pk, version=workspace.version, corrections=corrections, excluded=excluded)
        return Response(workspace_payload(workspace))

    @action(detail=True, methods=["get"])
    def rows(self, request, pk=None):
        workspace = self.get_object()
        source_id = serializers.IntegerField(min_value=1).run_validation(request.query_params.get("source_id"))
        source = get_object_or_404(workspace.sources, pk=source_id)
        page = serializers.IntegerField(min_value=1).run_validation(request.query_params.get("page", 1))
        rows = list(prepared_rows(source, include_excluded=True))
        return Response({"count": len(rows), "version": workspace.version, "results": rows[(page - 1) * 50:page * 50]})

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def duplicate_source(self, request, pk=None):
        workspace = self.get_object()
        serializer = SourceCopyInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        workspace = lock_workspace(workspace.pk, request.user, data["version"])
        source = get_object_or_404(workspace.sources, pk=data["source_id"])
        workspace, copied = add_source(workspace_id=workspace.pk, actor=request.user, version=workspace.version,
            rows=source.rows_json, filename=source.original_filename, sheet_name=source.sheet_name, entity_type=data["entity_type"])
        copied.corrections_json = source.corrections_json
        copied.excluded_json = source.excluded_json
        copied.save(update_fields=["corrections_json", "excluded_json"])
        return Response(workspace_payload(workspace))

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def remove_source(self, request, pk=None):
        workspace = self.get_object()
        serializer = SourceSelectionInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        workspace = lock_workspace(workspace.pk, request.user, serializer.validated_data["version"])
        source = get_object_or_404(workspace.sources, pk=serializer.validated_data["source_id"])
        source_id = source.pk
        source.delete()
        invalidate_preview(workspace)
        write_actor_audit_log(actor=request.user, action=AuditLog.Actions.UPDATE, instance=workspace,
            metadata={"kind": "import_source_removed", "source_id": source_id})
        return Response(workspace_payload(workspace))

    @action(detail=True, methods=["get"])
    def candidates(self, request, pk=None):
        from apps.businesses.access import Actions, assert_can, scope_queryset
        from .entities import MODELS, RESOURCES
        workspace = self.get_object()
        kind = serializers.ChoiceField(choices=["clients", "services", "specialists"]).run_validation(request.query_params.get("entity_type"))
        assert_can(request.user, workspace.business, RESOURCES[kind], Actions.VIEW)
        queryset = scope_queryset(MODELS[kind].objects.filter(business=workspace.business), request.user, workspace.business, RESOURCES[kind])
        if kind == "specialists":
            queryset = queryset.filter(resource_type="staff", is_active=True, retired_at__isnull=True)
        else:
            queryset = queryset.filter(is_archived=False)
        field = "full_name" if kind == "clients" else "name"
        search = serializers.CharField(max_length=100, allow_blank=True).run_validation(request.query_params.get("search", ""))
        if search:
            queryset = queryset.filter(**{field + "__icontains": search})
        return Response({"results": [{"id": obj.pk, "label": getattr(obj, field)} for obj in queryset.order_by(field, "pk")[:50]]})

    @action(detail=True, methods=["get"])
    def references(self, request, pk=None):
        from apps.businesses.access import Actions, assert_can
        from .entities import RESOURCES, accessible_entity
        workspace = self.get_object()
        kind = serializers.ChoiceField(choices=["clients", "services", "specialists"]).run_validation(request.query_params.get("entity_type"))
        assert_can(request.user, workspace.business, RESOURCES[kind], Actions.VIEW)
        reference = request.query_params.get("reference", "")
        if reference.startswith("crm:"):
            entity_id = serializers.IntegerField(min_value=1).run_validation(reference[4:])
            obj = accessible_entity(business=workspace.business, actor=request.user, entity_type=kind, pk=entity_id)
            return Response({"count": 1, "results": [{"reference": reference, "label": obj.full_name if kind == "clients" else obj.name}]})
        sources = workspace.sources.filter(entity_type=kind)
        if request.query_params.get("source_id"):
            source_id = serializers.IntegerField(min_value=1).run_validation(request.query_params["source_id"])
            sources = sources.filter(pk=source_id)
        page = serializers.IntegerField(min_value=1).run_validation(request.query_params.get("page", 1))
        search = serializers.CharField(max_length=100, allow_blank=True).run_validation(request.query_params.get("search", "")).casefold()
        results = []
        for source in sources.order_by("pk"):
            for row in prepared_rows(source):
                token = f"row:{source.pk}:{row['row']}"
                if reference and token != reference:
                    continue
                header = source.mapping_json.get("full_name" if kind == "clients" else "name")
                name = row["values"].get(header, "") if header else ""
                label = f"{name or source.original_filename} · {source.sheet_name or source.original_filename} · {row['row']}"
                if not search or search in label.casefold():
                    results.append({"reference": token, "label": label})
        return Response({"count": len(results), "results": results[(page - 1) * 50:page * 50]})

    @action(detail=True, methods=["get"])
    def profiles(self, request, pk=None):
        workspace = self.get_object()
        return Response({"results": list(ImportMappingProfile.objects.filter(business=workspace.business,
            actor=request.user).order_by("name", "pk").values("id", "name", "entity_type")[:100])})

    @action(detail=True, methods=["post"])
    def save_profile(self, request, pk=None):
        workspace = self.get_object()
        serializer = SaveProfileInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        workspace = save_profile(workspace_id=workspace.pk, actor=request.user, **serializer.validated_data)
        return Response(workspace_payload(workspace))

    @action(detail=True, methods=["post"])
    def apply_profile(self, request, pk=None):
        workspace = self.get_object()
        serializer = ApplyProfileInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        workspace = apply_profile(workspace_id=workspace.pk, actor=request.user, **serializer.validated_data)
        return Response(workspace_payload(workspace))

    @action(detail=True, methods=["get"])
    def activation(self, request, pk=None):
        return Response(activation_preview(self.get_object(), request.user))

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        workspace = self.get_object()
        serializer = ActivationInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        data.pop("confirmed")
        return Response(activate_records(workspace_id=workspace.pk, actor=request.user, **data))

    @action(detail=True, methods=["post"])
    def preview(self, request, pk=None):
        workspace = self.get_object()
        serializer = OperationInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        background = data.pop("background")
        if background:
            from .operations import request_operation
            workspace = request_operation(workspace_id=workspace.pk, actor=request.user, action="preview", **data)
        else:
            workspace = preview_workspace(workspace_id=workspace.pk, actor=request.user, **data)
        return Response(workspace_payload(workspace, actor=request.user))

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        workspace = self.get_object()
        serializer = OperationInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        background = data.pop("background")
        if background:
            from .operations import request_operation
            workspace = request_operation(workspace_id=workspace.pk, actor=request.user, action="confirm", **data)
        else:
            workspace = confirm_workspace(workspace_id=workspace.pk, actor=request.user, **data)
        return Response(workspace_payload(workspace, actor=request.user))

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def cancel(self, request, pk=None):
        workspace = self.get_object()
        serializer = VersionInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        workspace = lock_workspace(workspace.pk, request.user, serializer.validated_data["version"])
        workspace.sources.all().delete()
        invalidate_preview(workspace)
        workspace.state = ImportWorkspace.States.CANCELLED
        workspace.save(update_fields=["state", "updated_at"])
        write_actor_audit_log(actor=request.user, action=AuditLog.Actions.UPDATE, instance=workspace,
                             metadata={"kind": "import_cancelled", "source_data_removed": True})
        return Response(workspace_payload(workspace))

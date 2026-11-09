import hashlib
import json

from django.core.exceptions import ValidationError as ModelValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import IntegrityError, transaction
from rest_framework.exceptions import APIException, ValidationError

from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.models import Business
from apps.core.custom_fields import assert_custom_field_editable, validate_custom_field_value
from apps.core.models import CustomFieldDefinition, CustomFieldValue, ImportWorkspace
from apps.scheduling.import_commands import create_imported_record
from .drafts import StaleImportVersion, checked_rows, lock_workspace, prepared_rows
from .entities import accessible_entity, write_basic_entity
from .schema import ENTITY_NAMES, validate_fields
from .values import mapped_values
from .bindings import binding_key, bound_entity, remember_entity


ORDER = {"clients": 0, "services": 1, "specialists": 2, "appointments": 3}


def json_value(value):
    return json.loads(json.dumps(value, cls=DjangoJSONEncoder, ensure_ascii=False))


def fingerprint(report):
    stable = [{key: value for key, value in row.items() if key != "id"}
              for row in report["rows"]]
    return hashlib.sha256(json.dumps(stable, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class ImportRunner:
    def __init__(self, workspace, actor):
        self.workspace = workspace
        self.business = workspace.business
        self.actor = actor
        self.references = {}
        self.external_refs = {}
        self.definitions = {}
        self.rows = []
        self.errors = []
        self.targets = set()
        self.identities = set()

    def resolve(self, kind, token):
        if token.startswith("crm:") and token[4:].isdigit():
            return accessible_entity(business=self.business, actor=self.actor, entity_type=kind, pk=int(token[4:]))
        reference = self.references.get((kind, token)) or self.external_refs.get((kind, token))
        if reference is None:
            raise ValidationError({kind: "Select an existing CRM record or a valid source-row reference."})
        return reference

    def save_fields(self, source, obj, values, decision):
        if not values:
            return {}, False, {}
        assert_can(self.actor, self.business, Resources.SETTINGS, Actions.UPDATE)
        actual, changed, before = {}, False, {}
        for spec in source.fields_json:
            if spec["key"] not in values:
                continue
            key = (ENTITY_NAMES[source.entity_type], spec["key"])
            definition = self.definitions.get(key)
            if definition is None:
                if spec.get("definition_id"):
                    definition = CustomFieldDefinition.objects.select_for_update().get(pk=spec["definition_id"], business=self.business, entity_type=key[0])
                    assert_custom_field_editable(definition, self.actor)
                else:
                    definition = CustomFieldDefinition.objects.create(business=self.business, entity_type=key[0],
                        key=key[1], label=spec["label"], field_type=spec["field_type"],
                        options_json={"options": spec["options"], "display": {name: spec[name] for name in ("in_card", "in_table", "in_filters", "in_calendar")}})
                self.definitions[key] = definition
            value = validate_custom_field_value(definition=definition, value_json=values[spec["key"]])
            existing = CustomFieldValue.objects.select_for_update().filter(definition=definition, entity_type=key[0], entity_id=str(obj.pk)).first()
            before[spec["key"]] = existing.value_json if existing else {}
            action = decision.get("action", "create")
            should_write = action == "create" or (action == "fill" and (existing is None or existing.value_json.get("value") in (None, "")))
            should_write = should_write or (action == "update" and "custom." + spec["key"] in decision.get("update_fields", []))
            if should_write:
                changed = changed or existing is None or existing.value_json != value
                CustomFieldValue.objects.update_or_create(definition=definition, entity_type=key[0], entity_id=str(obj.pk),
                    defaults={"business": self.business, "value_json": value})
                actual[spec["key"]] = value
            else:
                actual[spec["key"]] = existing.value_json if existing else {}
        return actual, changed, before

    def run(self):
        sources = sorted(self.workspace.sources.all(), key=lambda source: (ORDER[source.entity_type], source.pk))
        specs = {}
        for source in sources:
            if checked_rows(source.rows_json) != source.digest:
                raise ValidationError("The stored source changed. Upload it again.")
            source.fields_json = validate_fields(source.fields_json, business=self.business, actor=self.actor, entity_type=source.entity_type)
            for field in source.fields_json:
                key = (source.entity_type, field["key"])
                if key in specs and specs[key] != field:
                    raise ValidationError("Additional field definitions must agree across sources.")
                specs[key] = field
        for source in sources:
            for row in prepared_rows(source, include_excluded=True):
                token = f"row:{source.pk}:{row['row']}"
                decision = source.resolutions_json.get(str(row["row"]), {})
                base = {"source_id": source.pk, "row": row["row"], "entity_type": source.entity_type, "reference": token}
                if row["excluded"] or decision.get("action") == "skip":
                    self.rows.append({**base, "outcome": "skipped", "values": {}, "custom": {}})
                    continue
                previous_definitions = dict(self.definitions)
                values = {}
                try:
                    with transaction.atomic():
                        values, custom, external_id = mapped_values(source, row["values"], self.business)
                        identity = binding_key(source, external_id, row["row"])
                        identity_token = tuple(identity.values())
                        if identity_token in self.identities:
                            raise ValidationError("The same source record appears more than once. Exclude the repeated row.")
                        bound = bound_entity(source, self.actor, identity)
                        before_values = {}
                        target = (source.entity_type, decision.get("target_id"))
                        if target[1] and target in self.targets:
                            raise ValidationError("One existing record cannot be updated by multiple source rows in the same draft.")
                        if external_id and (source.entity_type, external_id) in self.external_refs:
                            raise ValidationError({"external_id": "This source identifier is not unique."})
                        if bound is not None and not decision:
                            obj, outcome = bound, "unchanged"
                            before_version = obj.updated_at.isoformat()
                            if source.entity_type == "appointments":
                                assert_can(self.actor, self.business, Resources.CLIENTS, Actions.VIEW, obj=obj.client)
                                values.update(start_at=obj.start_at, end_at=obj.end_at, status=obj.status, notes=obj.notes,
                                    client_name=obj.client.full_name, service_name=obj.service.name, specialist_name=obj.resource.name if obj.resource else "",
                                    client_ref=f"crm:{obj.client_id}", service_ref=f"crm:{obj.service_id}", specialist_ref=f"crm:{obj.resource_id}",
                                    booked_price=obj.booked_price, booked_duration_minutes=obj.booked_duration_minutes)
                            else:
                                values = {key: getattr(obj, key) for key in values}
                            before_values = dict(values)
                            decision = {"action": "reuse", "target_id": obj.pk}
                        elif source.entity_type == "appointments":
                            if decision.get("action", "create") != "create" or decision.get("target_id"):
                                raise ValidationError("Existing appointments must be skipped; rescheduling is a separate command.")
                            client = self.resolve("clients", values["client_ref"])
                            service = self.resolve("services", values["service_ref"])
                            specialist = self.resolve("specialists", values["specialist_ref"])
                            from datetime import timedelta
                            values.update(client_name=client.full_name, service_name=service.name, specialist_name=specialist.name,
                                end_at=values["start_at"] + timedelta(minutes=service.duration_minutes))
                            obj = create_imported_record(business=self.business, actor=self.actor, client=client,
                                service=service, specialist=specialist, start_at=values["start_at"],
                                status=values.get("status", "created"), notes=values.get("notes", ""),
                                reason=values.get("reason", ""), import_reference=f"{self.workspace.pk}:{token}")
                            outcome, before_version = "created", None
                            values.update(client_name=client.full_name, service_name=service.name, specialist_name=specialist.name,
                                end_at=obj.end_at, booked_price=obj.booked_price, booked_duration_minutes=obj.booked_duration_minutes)
                        else:
                            obj, outcome, before_version, values, before_values = write_basic_entity(business=self.business, actor=self.actor,
                                entity_type=source.entity_type, values=values, decision=decision, reference=f"{self.workspace.pk}:{token}")
                        remember_entity(identity, obj)
                        custom, custom_changed, before_custom = self.save_fields(source, obj, custom, decision)
                        if custom_changed and outcome == "unchanged":
                            outcome = "updated"
                        if target[1]:
                            self.targets.add(target)
                        self.identities.add(identity_token)
                        self.references[(source.entity_type, token)] = obj
                        if external_id:
                            self.external_refs[(source.entity_type, external_id)] = obj
                        self.rows.append({**base, "id": obj.pk, "existing_id": decision.get("target_id"),
                            "outcome": outcome, "before_version": before_version, "before": json_value(before_values), "values": json_value({**values, "external_id": external_id}), "custom": custom, "before_custom": before_custom})
                except (APIException, ModelValidationError, IntegrityError) as exc:
                    self.definitions = previous_definitions
                    detail = {"conflict": "This row conflicts with current business data. Review it and check again."} if isinstance(exc, IntegrityError) else (
                        getattr(exc, "detail", None) or getattr(exc, "message_dict", None) or getattr(exc, "messages", ["Invalid row"]))
                    self.errors.append({**base, "errors": json_value(detail), "values": json_value(values)})
        return {"rows": self.rows, "errors": self.errors, "ready": bool(self.rows) and not self.errors,
            "summary": {key: sum(row["outcome"] == key for row in self.rows) for key in ("created", "updated", "unchanged", "skipped")}}


def simulate(workspace, actor):
    with transaction.atomic():
        report = ImportRunner(workspace, actor).run()
        transaction.set_rollback(True)
    # Temporary primary keys must never be used as live CRM links in preview.
    for row in report["rows"]:
        if not row.get("existing_id"):
            row.pop("id", None)
    report["fingerprint"] = fingerprint(report)
    return report


@transaction.atomic
def preview_workspace(*, workspace_id, actor, version, operation_token=None):
    workspace = lock_workspace(workspace_id, actor, version, operation_token=operation_token)
    Business.objects.select_for_update().get(pk=workspace.business_id)
    report = simulate(workspace, actor)
    workspace.version += 1
    workspace.report_json = report
    workspace.validated_version = workspace.version if report["ready"] else None
    workspace.state = ImportWorkspace.States.READY if report["ready"] else ImportWorkspace.States.DRAFT
    workspace.save(update_fields=["version", "report_json", "validated_version", "state", "updated_at"])
    return workspace


@transaction.atomic
def confirm_workspace(*, workspace_id, actor, version, operation_token=None):
    workspace = lock_workspace(workspace_id, actor, version, editable=False, operation_token=operation_token)
    if workspace.state == ImportWorkspace.States.IMPORTED:
        return workspace
    if workspace.state != ImportWorkspace.States.READY or workspace.validated_version != workspace.version:
        raise ValidationError("Check the current draft before confirming.")
    Business.objects.select_for_update().get(pk=workspace.business_id)
    report = simulate(workspace, actor)
    if not report["ready"] or report["fingerprint"] != workspace.report_json.get("fingerprint"):
        raise StaleImportVersion("Business data or permissions changed. Check the draft again.")
    result = ImportRunner(workspace, actor).run()
    if not result["ready"]:
        raise ValidationError({"rows": result["errors"]})
    if fingerprint(result) != workspace.report_json.get("fingerprint"):
        raise StaleImportVersion("Business data changed during confirmation. Check the draft again.")
    workspace.result_json = result
    workspace.state = ImportWorkspace.States.IMPORTED
    workspace.save(update_fields=["result_json", "state", "updated_at"])
    return workspace

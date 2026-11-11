"""Current, permission-scoped labels for reviewing an immutable command payload."""
from collections import defaultdict

from rest_framework.exceptions import PermissionDenied

from apps.ai_core.crm_tools import ENTITIES, scoped_entities, serialize_record
from apps.branches.access import accessible_branches
from apps.businesses.access import Resources
from apps.core.crm_read_scope import readable_queryset


CRM_FIELDS = {"client": "clients", "lead": "leads", "deal": "deals", "appointment": "appointments"}
MEMBER_FIELDS = {"assignee", "owner", "responsible_user", "user_id"}
CATALOG_FIELDS = {"service", "resource", "branch", "pipeline", "stage", "stage_id"}


def action_reviews(logs, *, business, user):
    from apps.accounts.models import User
    from apps.businesses.models import BusinessMember
    from apps.crm.models import Pipeline, PipelineStage
    from apps.scheduling.models import Resource
    from apps.services.models import Service

    requested = defaultdict(set)
    fields = set(CRM_FIELDS) | MEMBER_FIELDS | CATALOG_FIELDS
    for log in logs:
        for side in ("values", "before"):
            for field, value in (log.input_json.get(side) or {}).items():
                if field in fields and type(value) is int and 0 < value < 2**63:
                    requested[field].add(value)
    names = {}
    for field, ids in requested.items():
        if field in CRM_FIELDS:
            entity = CRM_FIELDS[field]
            try:
                rows = scoped_entities(business, user, entity, include_archived=True).filter(pk__in=ids)
                names[field] = {}
                for row in rows:
                    data = serialize_record(ENTITIES[entity], row, user)
                    names[field][row.pk] = data.get("full_name") or data.get("title") or data.get("message") or f"#{row.pk}"
            except PermissionDenied:
                names[field] = {}
        elif field in MEMBER_FIELDS:
            members = BusinessMember.objects.filter(business=business, is_active=True, user__is_active=True).values("user_id")
            names[field] = {row.pk: row.full_name or row.get_full_name() or row.username
                            for row in User.objects.filter(pk__in=ids).filter(pk__in=members)}
        elif field == "branch":
            names[field] = dict(accessible_branches(user, business).filter(pk__in=ids).values_list("pk", "name"))
        else:
            model, resource = {"service": (Service, Resources.SETTINGS), "resource": (Resource, Resources.SETTINGS),
                               "pipeline": (Pipeline, Resources.DEALS), "stage": (PipelineStage, Resources.DEALS),
                               "stage_id": (PipelineStage, Resources.DEALS)}[field]
            rows = readable_queryset(model.objects.filter(pk__in=ids), actor=user, business=business, resource=resource)
            if field in {"stage", "stage_id"}:
                rows = rows.filter(pipeline__business=business)
            names[field] = dict(rows.values_list("pk", "name"))
    result = {}
    for log in logs:
        review = {"timezone": business.timezone, "values": {}, "before": {}}
        for side in ("values", "before"):
            for field, value in (log.input_json.get(side) or {}).items():
                if field in fields and value is not None:
                    review[side][field] = names.get(field, {}).get(value) if type(value) is int else None
        result[log.pk] = review
    return result

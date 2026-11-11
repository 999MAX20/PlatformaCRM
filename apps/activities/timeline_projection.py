"""Batch current object labels through the same access boundary as history reads."""
from collections import defaultdict

from apps.businesses.access import Resources
from apps.core.crm_read_scope import readable_queryset


def timeline_objects(events, actor):
    from apps.clients.models import Client
    from apps.crm.models import Deal
    from apps.leads.models import Lead
    from apps.scheduling.models import Appointment
    from apps.tasks.models import Task
    from apps.conversations.models import Conversation

    models = {
        "client": (Client, Resources.CLIENTS, "full_name"),
        "lead": (Lead, Resources.LEADS, None),
        "deal": (Deal, Resources.DEALS, "title"),
        "task": (Task, Resources.TASKS, "title"),
        "appointment": (Appointment, Resources.APPOINTMENTS, None),
        "conversation": (Conversation, Resources.CONVERSATIONS, None),
    }
    groups = defaultdict(list)
    for event in events:
        if event.entity_type.lower() in models and str(event.entity_id).isascii() and str(event.entity_id).isdigit():
            if 0 < int(event.entity_id) < 2**63:
                groups[(event.business_id, event.entity_type.lower())].append(event)
    result = {}
    for (business_id, kind), rows in groups.items():
        model, resource, name_field = models[kind]
        queryset = readable_queryset(
            model.objects.filter(pk__in={int(row.entity_id) for row in rows}),
            actor=actor, business=rows[0].business, resource=resource,
        )
        if kind == "appointment":
            for item in queryset.select_related("service"):
                name = item.service.name if item.service.business_id == business_id else ""
                result[(business_id, kind, str(item.pk))] = name
            continue
        # Keep current names separate from historical changes. Do not reconstruct
        # history from today's status, assignment, dates or arbitrary metadata.
        fields = ["pk", name_field] if name_field else ["pk"]
        for values in queryset.values_list(*fields):
            result[(business_id, kind, str(values[0]))] = values[1] if name_field else ""
    return result


def timeline_reference_names(events, actor, objects):
    """Resolve historical IDs only within an authorized object's business."""
    from apps.accounts.models import User
    from apps.businesses.models import BusinessMember
    from apps.crm.models import Deal, PipelineStage
    from django.db.models import Q

    groups = defaultdict(list)
    for event in events:
        if (event.business_id, event.entity_type.lower(), event.entity_id) in objects:
            groups[event.business_id].append(event)
    result = {}
    def identifier(value):
        return value if type(value) is int and 0 < value < 2**63 else None
    for business_id, rows in groups.items():
        users, stages = set(), set()
        for row in rows:
            metadata = row.metadata if isinstance(row.metadata, dict) else {}
            users.update(identifier(metadata.get(key)) for key in ("from_assignee", "to_assignee", "from_owner", "to_owner"))
            if row.entity_type.lower() == "deal":
                stages.update(identifier(metadata.get(key)) for key in ("from_stage", "to_stage"))
        users.discard(None)
        stages.discard(None)
        names = {}
        if users:
            members = BusinessMember.objects.filter(business_id=business_id, is_active=True).values("user_id")
            names = {u.pk: u.full_name or u.get_full_name() for u in User.objects.filter(Q(pk__in=members) | Q(pk=rows[0].business.owner_id), pk__in=users)}
        stage_names, pipelines = {}, {}
        if stages:
            deals = readable_queryset(Deal.objects.filter(pk__in=[r.entity_id for r in rows if r.entity_type.lower() == "deal"]), actor=actor, business=rows[0].business, resource=Resources.DEALS)
            pipelines = {str(pk): pipeline for pk, pipeline in deals.values_list("pk", "pipeline_id")}
            stage_names = {(s.pk, s.pipeline_id): s.name for s in PipelineStage.objects.filter(business_id=business_id, pipeline__business_id=business_id, pk__in=stages)}
        for row in rows:
            metadata = row.metadata if isinstance(row.metadata, dict) else {}
            resolved = {}
            for side in ("from", "to"):
                user_id = identifier(metadata.get(f"{side}_assignee", metadata.get(f"{side}_owner")))
                if user_id in names:
                    resolved[f"{side}_assignee"] = names[user_id]
                stage = stage_names.get((identifier(metadata.get(f"{side}_stage")), pipelines.get(row.entity_id))) if row.entity_type.lower() == "deal" else None
                if stage:
                    resolved[f"{side}_stage"] = stage
            result[row.pk] = resolved
    return result

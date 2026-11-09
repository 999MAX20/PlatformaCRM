"""One approved transaction for a client and their dated visits."""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.ai_core.crm_tools import ENTITIES, request_context, scoped_entities, validated_details
from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.models import Business
from apps.clients.models import Client
from apps.scheduling.models import Appointment, Resource
from apps.services.models import Service


MAX_VISITS = 30


def name_matches(queryset, name):
    # Python casefold also handles Cyrillic on the local SQLite backend. Only
    # names/IDs from the permission-scoped queryset enter this comparison.
    key = " ".join(name.split()).casefold()
    return [pk for pk, label in queryset.values_list("pk", "full_name").iterator()
            if " ".join(label.split()).casefold() == key]


def schedule_access(business, user, values):
    scoped_entities(business, user, "appointments")
    clients = scoped_entities(business, user, "clients")
    assert_can(user, business, Resources.APPOINTMENTS, Actions.CREATE)
    data = values.get("client", {})
    if data.get("id"):
        client = clients.filter(pk=data["id"]).first()
        if client is None:
            raise PermissionDenied("Client is unavailable.")
        return client, None
    matches = name_matches(clients, data.get("full_name", ""))
    if len(matches) > 1:
        raise ValidationError({"client": "Select one of the matching clients."})
    if matches:
        return clients.get(pk=matches[0]), None
    assert_can(user, business, Resources.CLIENTS, Actions.CREATE)
    serializer = validated_details(business=business, user=user, spec=ENTITIES["clients"],
        entity="clients", tool="crm_create", target=None, values=data)
    return Client(**serializer.validated_data), serializer


def _shape(values):
    if not isinstance(values, dict) or set(values) != {"client", "visits", "plan"}:
        raise ValidationError("Invalid scheduling request.")
    client, visits = values["client"], values["visits"]
    if not isinstance(client, dict) or not client or set(client) - {"id", "full_name", "phone"}:
        raise ValidationError({"client": "Provide a client."})
    if "id" in client:
        if set(client) != {"id"} or type(client["id"]) is not int or client["id"] <= 0:
            raise ValidationError({"client": "Invalid client selection."})
    elif not isinstance(client.get("full_name"), str) or not client["full_name"].strip():
        raise ValidationError({"client": "Provide the client name."})
    if type(values["plan"]) is not bool or not isinstance(visits, list) or not 1 <= len(visits) <= MAX_VISITS:
        raise ValidationError({"visits": "Provide between 1 and 30 visits."})
    if not values["plan"] and len(visits) != 1:
        raise ValidationError({"visits": "Multiple visits require a plan."})
    for visit in visits:
        if not isinstance(visit, dict) or set(visit) != {
                "service", "resource", "branch", "start_at", "expected_price", "expected_duration_minutes"}:
            raise ValidationError({"visits": "Invalid visit fields."})
        for field in ("service", "resource"):
            if type(visit[field]) is not int or visit[field] <= 0:
                raise ValidationError({field: "Select a current record."})
        if visit["branch"] is not None and (type(visit["branch"]) is not int or visit["branch"] <= 0):
            raise ValidationError({"branch": "Invalid branch."})
        if type(visit["expected_duration_minutes"]) is not int or visit["expected_duration_minutes"] <= 0:
            raise ValidationError({"service": "Invalid duration."})


def assert_schedule_allowed(business, user, values):
    from apps.branches.access import assert_branch_access
    from apps.branches.models import Branch
    _shape(values)
    client, _ = schedule_access(business, user, values)
    for visit in values["visits"]:
        resource = Resource.objects.filter(pk=visit["resource"], business=business).first()
        if resource is None:
            raise PermissionDenied("Specialist is unavailable.")
        branch = None
        if visit["branch"]:
            branch = Branch.objects.filter(pk=visit["branch"], business=business).first()
            if branch is None:
                raise PermissionDenied("Branch is unavailable.")
            assert_branch_access(user, business, branch)
        candidate = Appointment(business=business, client=client, resource=resource, branch=branch)
        assert_can(user, business, Resources.APPOINTMENTS, Actions.VIEW, obj=candidate)
        assert_can(user, business, Resources.APPOINTMENTS, Actions.CREATE, obj=candidate)


def validate_schedule(*, business, user, values, lock=False):
    from apps.branches.access import assert_branch_access
    from apps.branches.models import Branch
    from apps.branches.schedule import appointment_snapshot
    from apps.scheduling.availability import validate_appointment_availability
    from apps.scheduling.record_commands import validate_responsible
    _shape(values)
    client, serializer = schedule_access(business, user, values)
    validate_responsible(business=business, actor=user, user=user)
    resolved, occupied = [], []
    for visit in values["visits"]:
        services = Service.objects.filter(business=business, is_active=True, is_archived=False)
        if lock:
            services = services.select_for_update()
        service = services.filter(pk=visit["service"]).first()
        resource = Resource.objects.filter(business=business, pk=visit["resource"], is_active=True,
            retired_at__isnull=True, resource_type=Resource.ResourceTypes.STAFF).first()
        if service is None or resource is None:
            raise ValidationError({"visits": "The service or specialist is unavailable."})
        branch = None
        if visit["branch"] is not None:
            branch = Branch.objects.filter(business=business, pk=visit["branch"], is_active=True, archived_at__isnull=True).first()
            if branch is None:
                raise ValidationError({"branch": "The branch is unavailable."})
        snapshot = appointment_snapshot(business, service, resource, branch)
        branch = snapshot["branch"]
        if branch:
            assert_branch_access(user, business, branch, active=True)
        candidate = Appointment(business=business, client=client, service=service, resource=resource, branch=branch)
        assert_can(user, business, Resources.APPOINTMENTS, Actions.CREATE, obj=candidate)
        assert_can(user, business, Resources.APPOINTMENTS, Actions.VIEW, obj=candidate)
        try:
            start = parse_datetime(visit["start_at"])
            price = Decimal(str(visit["expected_price"])) if visit["expected_price"] is not None else None
            if start is None or timezone.is_naive(start) or start <= timezone.now():
                raise ValueError
            if snapshot["booked_price"] != price or snapshot["booked_duration_minutes"] != visit["expected_duration_minutes"]:
                raise ValidationError({"service": "Booking terms changed. Request current terms."})
            end = validate_appointment_availability(business, service, start, resource=resource, branch=branch)
        except (ValueError, TypeError, ArithmeticError):
            raise ValidationError({"start_at": "Select an available future time."}) from None
        from apps.scheduling.resource_booking import required_resources
        resource_ids = {resource.pk, *(item.pk for item in required_resources(business, service, branch))}
        if any(resource_ids.intersection(ids) and start < other_end and end > other_start for ids, other_start, other_end in occupied):
            raise ValidationError({"start_at": "Visits overlap within this request."})
        occupied.append((resource_ids, start, end))
        resolved.append({"service": service, "resource": resource, "branch": branch, "start_at": start,
            "expected_price": price, "expected_duration_minutes": visit["expected_duration_minutes"]})
    return client, serializer, resolved


@transaction.atomic
def execute_schedule(log, user):
    from apps.ai_core.crm_tools import serialize_record
    from apps.ai_core.crm_writes import save_details
    from apps.scheduling.plan_services import change_plan, create_plan
    from apps.scheduling.record_commands import create_record
    business = Business.objects.select_for_update().get(pk=log.business_id)
    client, serializer, visits = validate_schedule(business=business, user=user, values=log.input_json["values"], lock=True)
    created_client = serializer is not None
    if serializer:
        client = save_details(serializer, entity="clients", actor=user, request=request_context(user))
    plan, appointments = None, []
    if log.input_json["values"]["plan"]:
        steps = [{key: visit[key] for key in ("service", "resource", "branch")} for visit in visits]
        plan, _ = create_plan(business=business, actor=user, client=client, steps=steps,
            idempotency_key=f"voice-plan:{log.pk}")
        for step, visit in zip(plan.steps.order_by("position"), visits):
            plan, _ = change_plan(plan=plan, actor=user, command="schedule", expected_revision=plan.revision,
                idempotency_key=f"voice-plan:{log.pk}:{step.pk}", data={"step_id": step.pk, **visit_without_service(visit)})
            step.refresh_from_db()
            appointments.append(step.appointment)
    else:
        appointments.append(create_record(business=business, actor=user, client=client, **visits[0]))
    records = [{"entity": "clients", "entity_id": client.pk, "created": created_client,
                "record": serialize_record(ENTITIES["clients"], client, user)}]
    records.extend({"entity": "appointments", "entity_id": row.pk, "created": True,
                    "record": {**serialize_record(ENTITIES["appointments"], row, user),
                        "service_name": row.service.name, "resource_name": row.resource.name,
                        "branch_name": row.branch_name}} for row in appointments)
    return {"entity": "appointments", "entity_id": appointments[0].pk, "record": records[1]["record"],
            "records": records, "visit_plan_id": plan.pk if plan else None}


def visit_without_service(visit):
    return {key: value for key, value in visit.items() if key != "service"}

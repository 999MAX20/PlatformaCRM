from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.businesses.access import Actions, Resources, assert_can, can, scope_queryset
from apps.businesses.capabilities import assert_resource_enabled
from apps.clients.models import Client
from apps.scheduling.models import Appointment, Resource
from apps.services.models import Service
from apps.branches.access import accessible_branches
from .audit import write_patient_audit
from .encounter_services import primary_draft_context
from .models import ReceptionBookingRequest
from .patient_selectors import reception_context
from .role_access import assert_medical_branch_permission
from .reception_claims import reception_request_context
from .reception_contacts import expiry_ready


def _rows(items, actor, business, *, can_manage=False):
    results = []
    now = timezone.now()
    branch_ids = set(accessible_branches(actor, business).values_list("pk", flat=True))
    for item in items:
        appointment = item.booked_appointment
        visible_appointment = (appointment is not None and appointment.business_id == business.pk
            and appointment.client_id == item.patient.client_id and appointment.branch_id in branch_ids) and can(actor, business, Resources.APPOINTMENTS,
            Actions.VIEW, obj=appointment).allowed
        assigned_to_me = bool(item.assignee_id and item.assignee.user_id == actor.pk)
        open_request = item.state in ("new", "pending")
        write_patient_audit(actor=actor, business=business, patient=item.patient, action="read")
        results.append({"id": item.pk, "patient_id": item.patient_id, "client_id": item.patient.client_id,
            "client_name": item.patient.client.full_name, "branch_id": item.branch_id,
            "source_appointment_id": item.source_appointment_id, "service_id": item.service_id,
            "service_name": item.service.name, "preferred_resource_id": item.preferred_resource_id,
            "preferred_resource_name": item.preferred_resource.name,
            "referring_clinician_name": item.referring_clinician.user.full_name,
            "assignee_id": item.assignee_id, "assignee_name": item.assignee.user.full_name if item.assignee_id else None,
            "assigned_to_me": assigned_to_me,
            "actions": {"claim": can_manage and open_request and item.assignee_id is None,
                "contact": can_manage and assigned_to_me and item.state == "pending",
                "expire": can_manage and assigned_to_me and item.state == "pending" and expiry_ready(item, now),
                "reopen": can_manage and (item.state in ("declined", "expired", "cancelled") or
                    visible_appointment and item.state == "booked" and appointment.status == "cancelled"),
                "transfer": can_manage and assigned_to_me and item.state == "pending",
                "book": can_manage and assigned_to_me and item.state == "pending" and
                    can(actor, business, Resources.APPOINTMENTS, Actions.CREATE).allowed and
                    can(actor, business, Resources.APPOINTMENTS, Actions.VIEW).allowed,
                "link": can_manage and assigned_to_me and item.state == "pending" and
                    can(actor, business, Resources.APPOINTMENTS, Actions.UPDATE).allowed and
                    can(actor, business, Resources.APPOINTMENTS, Actions.VIEW).allowed},
            "created_at": item.created_at, "recommended_from": item.recommended_from,
            "recommended_until": item.recommended_until, "duration_minutes": item.duration_minutes,
            "patient_in_clinic": item.patient_in_clinic, "acceptance_due_at": item.acceptance_due_at,
            "contact_cycle": item.contact_cycle, "contact_due_at": item.contact_due_at,
            "contact_attempts": item.contact_attempts.filter(cycle=item.contact_cycle).count(),
            "closure_reason": item.closure_reason,
            "overdue": bool(item.assignee_id is None and item.state in ("new", "pending") and
                item.acceptance_due_at is not None and item.acceptance_due_at < now),
            "state": item.state, "revision": item.revision,
            "booked_appointment_id": appointment.pk if visible_appointment else None,
            "appointment_status": appointment.status if visible_appointment else None,
            "appointment_start_at": appointment.start_at if visible_appointment else None})
    return results


def _requests(business):
    return ReceptionBookingRequest.objects.select_related("patient__client", "service", "preferred_resource",
        "referring_clinician__user", "assignee__user", "booked_appointment").filter(business=business,
        patient__business=business, patient__client__business=business, branch__business=business,
        source_appointment__business=business, service__business=business, preferred_resource__business=business,
        referring_clinician__business=business)


def _page(offset, limit):
    if type(offset) is not int or not 0 <= offset <= 10000 or type(limit) is not int or not 1 <= limit <= 50:
        raise ValidationError({"pagination": "Provide an offset up to 10000 and a limit from 1 to 50."})


@transaction.atomic
def list_reception_candidates(*, actor, business_id, request_id, offset=0, limit=25):
    _page(offset, limit)
    actor, business, member, item = reception_request_context(actor=actor, business_id=business_id, request_id=request_id)
    if item.assignee_id != member.pk:
        raise PermissionDenied()
    assert_resource_enabled(business, Resources.APPOINTMENTS)
    for action in (Actions.VIEW, Actions.UPDATE):
        assert_can(actor, business, Resources.APPOINTMENTS, action)
    items = Appointment.objects.filter(business=business, client_id=item.patient.client_id,
        branch=item.branch, service=item.service, resource__business=business, resource__resource_type="staff",
        is_archived=False, status__in=("created", "confirmed", "rescheduled"), start_at__gt=timezone.now())
    items = items.exclude(pk=item.source_appointment_id).exclude(pk__in=ReceptionBookingRequest.objects.filter(
        business=business, booked_appointment__isnull=False).values("booked_appointment_id"))
    for action in (Actions.VIEW, Actions.UPDATE):
        items = scope_queryset(items, actor, business, Resources.APPOINTMENTS, action)
    if item.state != "pending":
        items = items.none()
    page = list(items.order_by("start_at", "pk").values("id", "start_at", "end_at", "updated_at", "resource__name")[offset:offset + limit + 1])
    write_patient_audit(actor=actor, business=business, patient=item.patient, action="read")
    return {"results": [{"id": row["id"], "start_at": row["start_at"], "end_at": row["end_at"],
        "updated_at": row["updated_at"], "resource_name": row["resource__name"]} for row in page[:limit]],
        "next_offset": offset + limit if len(page) > limit else None}


@transaction.atomic
def list_reception_requests(*, actor, business_id, branch_id, offset=0, limit=25, state=None):
    _page(offset, limit)
    if state is not None and state not in ReceptionBookingRequest.States.values:
        raise ValidationError({"state": "Select a supported request state."})
    actor, business, branch = reception_context(actor=actor, business_id=business_id, branch_id=branch_id, action="view")
    try:
        assert_medical_branch_permission(actor, business, "medical_patients", "update", branch=branch)
        can_manage = True
    except PermissionDenied:
        can_manage = False
    clients = scope_queryset(Client.objects.filter(business=business, is_archived=False), actor, business,
        Resources.CLIENTS, Actions.VIEW)
    items = _requests(business).filter(branch=branch, patient__client_id__in=clients.values("pk"))
    if state is not None:
        items = items.filter(state=state)
    page = list(items.order_by("-patient_in_clinic", "created_at", "pk")[offset:offset + limit + 1])
    return {"results": _rows(page[:limit], actor, business, can_manage=can_manage),
        "next_offset": offset + limit if len(page) > limit else None}


@transaction.atomic
def list_primary_follow_ups(*, actor, business_id, patient_id, encounter_id, participation_id=None, offset=0, limit=25):
    _page(offset, limit)
    business, patient, encounter, _ = primary_draft_context(actor=actor, business_id=business_id,
        patient_id=patient_id, encounter_id=encounter_id, participation_id=participation_id)
    page = list(_requests(business).filter(patient=patient, source_appointment_id=encounter.appointment_id)
        .order_by("-created_at", "-pk")[offset:offset + limit + 1])
    return {"results": _rows(page[:limit], actor, business), "next_offset": offset + limit if len(page) > limit else None}


@transaction.atomic
def list_follow_up_options(*, actor, business_id, patient_id, encounter_id, kind,
                          participation_id=None, search="", offset=0, limit=25):
    _page(offset, limit)
    if kind not in ("service", "staff") or not isinstance(search, str) or len(search) > 120:
        raise ValidationError({"options": "Select services or staff and a search up to 120 characters."})
    business, patient, encounter, _ = primary_draft_context(actor=actor, business_id=business_id,
        patient_id=patient_id, encounter_id=encounter_id, participation_id=participation_id)
    if kind == "service":
        items = Service.objects.filter(business=business, is_active=True, is_archived=False)
        default_id = encounter.appointment.service_id
    else:
        items = Resource.objects.filter(business=business, resource_type="staff", is_active=True,
            retired_at__isnull=True, archived_at__isnull=True)
        default_id = encounter.appointment.resource_id
    default = items.filter(pk=default_id).values("id", "name").first()
    page = list(items.filter(name__icontains=search.strip()).order_by("name", "pk")
        .values("id", "name")[offset:offset + limit + 1])
    write_patient_audit(actor=actor, business=business, patient=patient, action="read")
    return {"results": page[:limit], "default": default,
        "next_offset": offset + limit if len(page) > limit else None}

from django.db import transaction
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.businesses.models import BusinessMember
from apps.core.models import AuditLog
from .audit import write_patient_audit
from .reception_claims import reception_request_context
from .reception_selectors import _page
from .reception_transfer import reception_recipient


@transaction.atomic
def list_reception_recipients(*, actor, business_id, request_id, offset=0, limit=25, search=""):
    _page(offset, limit)
    if not isinstance(search, str) or len(search) > 120:
        raise ValidationError({"search": "Search with at most 120 characters."})
    actor, business, member, item = reception_request_context(actor=actor, business_id=business_id, request_id=request_id)
    if item.assignee_id != member.pk or item.state != "pending":
        raise PermissionDenied()
    candidates = BusinessMember.objects.filter(business=business, is_active=True, user__is_active=True,
        medical_role_assignment__kind="reception", medical_role_assignment__revoked_at__isnull=True).exclude(pk=member.pk)
    if search.strip():
        candidates = candidates.filter(Q(user__full_name__icontains=search.strip()) | Q(user__first_name__icontains=search.strip()) |
            Q(user__last_name__icontains=search.strip()) | Q(user__username__icontains=search.strip()) |
            Q(user__email__icontains=search.strip()))
    candidates = list(candidates.order_by("pk").values_list("pk", flat=True)[offset:offset + limit + 1])
    results = []
    for identifier in candidates[:limit]:
        try:
            recipient = reception_recipient(business=business, item=item, member_id=identifier)
        except PermissionDenied:
            continue
        results.append({"id": recipient.pk, "name": recipient.user.full_name or recipient.user.get_full_name() or recipient.user.get_username()})
    write_patient_audit(actor=actor, business=business, patient=item.patient, action="read")
    return {"results": results, "next_offset": offset + limit if len(candidates) > limit else None}


@transaction.atomic
def list_reception_history(*, actor, business_id, request_id, offset=0, limit=25):
    _page(offset, limit)
    actor, business, _, item = reception_request_context(actor=actor, business_id=business_id,
        request_id=request_id, action="view")
    kinds = ("medical_follow_up_requested", "medical_follow_up_claimed", "medical_follow_up_booked",
             "medical_follow_up_linked", "medical_follow_up_transferred", "medical_follow_up_contact")
    events = list(AuditLog.objects.filter(business=business, entity_type="ReceptionBookingRequest",
        entity_id=str(item.pk), metadata__kind__in=kinds).select_related("actor").order_by("-created_at", "-pk")[offset:offset + limit + 1])
    member_ids = {event.metadata.get(field) for event in events[:limit] for field in ("from_member_id", "to_member_id")
                  if type(event.metadata.get(field)) is int}
    members = {member.pk: member.user.full_name or member.user.get_full_name() or member.user.get_username()
               for member in BusinessMember.objects.filter(business=business, pk__in=member_ids).select_related("user")}
    results = [{"id": event.pk, "created_at": event.created_at, "kind": event.metadata["kind"],
        "actor_name": (event.actor.full_name or event.actor.get_full_name() or event.actor.get_username()) if event.actor else None,
        "from_name": members.get(event.metadata.get("from_member_id")),
        "to_name": members.get(event.metadata.get("to_member_id")),
        "outcome": event.metadata.get("outcome"), "cycle": event.metadata.get("cycle"),
        "reason": event.metadata.get("reason", "") if event.metadata["kind"] in ("medical_follow_up_transferred", "medical_follow_up_contact") else ""}
        for event in events[:limit]]
    write_patient_audit(actor=actor, business=business, patient=item.patient, action="read")
    return {"results": results, "next_offset": offset + limit if len(events) > limit else None}

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from apps.core.domain_errors import InvalidTransition

from .audit import write_patient_audit
from .models import TreatmentParticipation
from .participation_services import participation_context, _positive
from .participation_obligations import participation_obligations
from .role_access import assert_medical_branch_permission


@transaction.atomic
def read_participation_closure(*, actor, business_id, patient_id, participation_id, offset=0, limit=20, as_head=False):
    _positive(participation_id=participation_id)
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 50:
        raise ValidationError({"pagination": "Provide a valid offset and limit."})
    actor, business, patient, role = participation_context(actor, business_id, patient_id, "view")
    item = TreatmentParticipation.objects.select_related("branch", "member").filter(
        pk=participation_id, patient=patient, member__business=business, branch__business=business).first()
    if item is None:
        raise PermissionDenied()
    own = item.member_id == role.member_id and not as_head
    action = "update" if own else "manage"
    if not own and role.kind != "head":
        raise PermissionDenied()
    assert_medical_branch_permission(actor, business, "medical_participation", action,
        branch=item.branch, require_active=own)
    active = item.state == "active" and item.accepted_at is not None and item.accepted_at <= timezone.now()
    if not active:
        raise InvalidTransition("Participation is no longer active; reload its state.")
    remaining = participation_obligations(business=business, patient=patient, member=item.member, offset=offset, limit=limit)
    write_patient_audit(actor=actor, business=business, patient=patient, action="read", participation=item)
    return {"id": item.pk, "revision": item.revision, "state": item.state, "own": own,
        "can_end": active and own and not any(row["count"] for row in remaining.values()),
        "obligations": remaining, "next_offset": offset + limit if any(row["count"] > offset + limit for row in remaining.values()) else None}

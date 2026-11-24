from datetime import datetime
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.branches.models import Branch
from apps.businesses.models import BusinessMember
from apps.core.audit import write_actor_audit_log
from apps.core.domain_errors import InvalidTransition, ModuleDisabled
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from apps.core.models import AuditLog
from .identity_crypto import medical_request_digest
from .models import ReceptionDuty
from .patient_selectors import reception_context
from .role_services import _owner_context, _key


def duty_member(business, branch_id, identifier):
    member = BusinessMember.objects.select_related("user").filter(pk=identifier, business=business, is_active=True, user__is_active=True).first()
    if member is None:
        raise PermissionDenied()
    reception_context(actor=member.user, business_id=business.pk, branch_id=branch_id, action="update")
    return member


def current_duty_recipient(item, now):
    from .reception_transfer import reception_recipient
    duty = ReceptionDuty.objects.filter(business_id=item.business_id, branch_id=item.branch_id,
        starts_at__lte=now, ends_at__gt=now).first()
    if duty:
        for identifier in ([duty.lead_id] if duty.lead_available else []) + [duty.deputy_id]:
            if identifier is not None:
                try:
                    return reception_recipient(business=item.business, item=item, member_id=identifier)
                except (PermissionDenied, ModuleDisabled):
                    continue
    return None


@transaction.atomic
def save_reception_duty(*, actor, business_id, branch_id, lead_id, deputy_id, lead_available,
                        starts_at, ends_at, expected_revision, reason, idempotency_key):
    actor, business = _owner_context(actor, business_id)
    _key(idempotency_key)
    if type(expected_revision) is not int or expected_revision < 0 or type(lead_available) is not bool:
        raise ValidationError({"revision": "Provide the current revision and availability."})
    if (not isinstance(reason, str) or not reason.strip() or len(reason.strip()) > 1000 or
            not isinstance(starts_at, datetime) or not isinstance(ends_at, datetime) or
            timezone.is_naive(starts_at) or timezone.is_naive(ends_at) or ends_at <= starts_at):
        raise ValidationError({"duty": "Provide a reason and a valid timezone-aware duty period."})
    branch = Branch.objects.filter(pk=branch_id, business=business, is_active=True, archived_at__isnull=True).first()
    if branch is None:
        raise PermissionDenied()
    lead = duty_member(business, branch_id, lead_id)
    deputy = duty_member(business, branch_id, deputy_id) if deputy_id is not None else None
    if lead_id == deputy_id:
        raise ValidationError({"deputy_id": "Select a different deputy."})
    def operation():
        item = ReceptionDuty.objects.select_for_update().filter(branch=branch, business=business).first()
        if expected_revision != (item.revision if item else 0):
            raise InvalidTransition("The duty configuration changed; reload it.")
        if item is None: item = ReceptionDuty(business=business, branch=branch, revision=0)
        item.lead, item.deputy, item.lead_available = lead, deputy, lead_available
        item.starts_at, item.ends_at, item.revision = starts_at, ends_at, item.revision + 1
        item.full_clean(); item.save()
        write_actor_audit_log(actor=actor, business=business, action=AuditLog.Actions.UPDATE, instance=item,
            metadata={"kind": "medical_reception_duty", "lead": lead_id, "deputy": deputy_id,
                "available": lead_available, "start": starts_at.isoformat(), "end": ends_at.isoformat(),
                "revision": item.revision, "reason": reason.strip()})
        return CRMCommandResult(data={"revision": item.revision}, resource=item)
    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.reception.duty",
        idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business_id),
        payload={"branch": branch_id, "lead": lead_id, "deputy": deputy_id, "available": lead_available,
            "start": starts_at.isoformat(), "end": ends_at.isoformat(), "revision": expected_revision, "reason": reason.strip()}, operation=operation)
    return result.data | {"replayed": result.replayed}


@transaction.atomic
def read_reception_duty(*, actor, business_id, branch_id=None, after_id=0, search="", kind="branches"):
    _, business = _owner_context(actor, business_id)
    if kind not in ("branches", "members") or type(after_id) is not int or after_id < 0 or len(search) > 100:
        raise ValidationError({"page": "Select valid duty options."})
    if kind == "branches":
        rows = list(Branch.objects.filter(business=business, is_active=True, archived_at__isnull=True,
            pk__gt=after_id, name__icontains=search).order_by("pk")[:26])
        return {"results": [{"id": row.pk, "name": row.name} for row in rows[:25]], "next_id": rows[24].pk if len(rows) > 25 else None}
    branch = Branch.objects.filter(pk=branch_id, business=business, is_active=True, archived_at__isnull=True).first()
    if branch is None: raise PermissionDenied()
    from django.db.models import Q
    candidates = list(BusinessMember.objects.select_related("user").filter(business=business, is_active=True,
        pk__gt=after_id, user__is_active=True, medical_role_assignment__kind="reception",
        medical_role_assignment__revoked_at__isnull=True).filter(Q(user__full_name__icontains=search) |
        Q(user__email__icontains=search)).order_by("pk")[:26])
    results = []
    for row in candidates[:25]:
        try: duty_member(business, branch_id, row.pk)
        except PermissionDenied: continue
        results.append({"id": row.pk, "name": row.user.full_name or row.user.email})
    duty = ReceptionDuty.objects.filter(business=business, branch=branch).first()
    value = None if duty is None else {"revision": duty.revision, "lead_id": duty.lead_id,
        "deputy_id": duty.deputy_id, "lead_available": duty.lead_available, "starts_at": duty.starts_at, "ends_at": duty.ends_at}
    return {"results": results, "next_id": candidates[24].pk if len(candidates) > 25 else None, "duty": value}

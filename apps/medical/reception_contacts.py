from datetime import datetime, timedelta, timezone as utc
from zoneinfo import ZoneInfo

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.branches.schedule import day_intervals, normalize_intervals
from apps.core.audit import write_actor_audit_log
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from apps.core.models import AuditLog
from apps.scheduling.models import WorkingHours
from .identity_crypto import medical_request_digest
from .models import ReceptionBookingRequest, ReceptionContactAttempt
from .reception_claims import reception_request_context
from .reception_deadlines import reception_acceptance_deadline


def contact_work_intervals(item, date):
    branch = item.branch
    if branch.uses_business_defaults:
        row = WorkingHours.objects.filter(business=item.business, resource__isnull=True, weekday=date.weekday()).first()
        return [] if row is None or row.is_day_off else normalize_intervals([
            {"start": row.start_time.strftime("%H:%M"), "end": row.end_time.strftime("%H:%M")}])
    return normalize_intervals(day_intervals(branch, None, date=date))


def contact_deadline(item, now):
    zone = ZoneInfo(item.business.timezone)
    start = now.astimezone(zone).date()
    days = 0
    for offset in range(366):
        date = start + timedelta(days=offset)
        intervals = contact_work_intervals(item, date)
        ends = [datetime.combine(date, datetime.strptime(row["end"], "%H:%M").time(), zone) for row in intervals]
        if not ends or max(ends) <= now:
            continue
        days += 1
        if days == 2:
            return max(ends).astimezone(utc.utc)
    return None


def expiry_ready(item, now):
    if item.contact_due_at is None or now < item.contact_due_at:
        return False
    zone = ZoneInfo(item.business.timezone)
    attempts = item.contact_attempts.filter(cycle=item.contact_cycle).order_by("created_at", "pk")
    if attempts.filter(outcome="contacted").exists():
        return False
    days = set()
    for attempt in attempts:
        local = attempt.created_at.astimezone(zone)
        if any(row["start"] <= local.strftime("%H:%M") < row["end"] for row in contact_work_intervals(item, local.date())):
            days.add(local.date())
    return len(days) >= 2


@transaction.atomic
def update_reception_contact(*, actor, business_id, request_id, expected_revision, action, reason, idempotency_key):
    if action not in {"no_answer", "contacted", "declined", "expired", "cancelled", "reopen"}:
        raise ValidationError({"action": "Select a contact result or lifecycle action."})
    if type(expected_revision) is not int or expected_revision < 1:
        raise ValidationError({"expected_revision": "Provide the current revision."})
    if not isinstance(reason, str) or not reason.strip() or len(reason.strip()) > 1000:
        raise ValidationError({"reason": "Provide an organizational note or reason."})
    if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 128:
        raise ValidationError({"idempotency_key": "Provide an idempotency key."})
    actor, business, member, item = reception_request_context(actor=actor, business_id=business_id, request_id=request_id)
    if action != "reopen" and item.assignee_id != member.pk:
        raise PermissionDenied()
    reason = reason.strip()

    def operation():
        if item.revision != expected_revision:
            raise InvalidTransition("The request changed; reload it.")
        now = timezone.now()
        previous_booking = item.booked_appointment_id
        if action == "reopen":
            if item.state not in ("declined", "expired", "cancelled") and not (
                    item.state == "booked" and item.booked_appointment.status == "cancelled"):
                raise InvalidTransition("Only closed work or a cancelled booking can be reopened.")
            if ReceptionBookingRequest.objects.filter(business=business, patient=item.patient,
                    source_appointment=item.source_appointment, service=item.service, state__in=["new", "pending"]).exclude(pk=item.pk).exists():
                raise InvalidTransition("Another open request already exists for this referral.")
            item.state, item.assignee, item.claimed_at = "new", None, None
            item.closed_at, item.closure_reason, item.booked_appointment = None, "", None
            item.contact_cycle += 1
            item.contact_started_at, item.contact_due_at = None, None
            item.acceptance_due_at = reception_acceptance_deadline(business=business, branch_id=item.branch_id,
                requested_at=now, patient_in_clinic=False)
            item.patient_in_clinic = False
        else:
            if item.state != "pending":
                raise InvalidTransition("Accept an open request before recording its outcome.")
            if action in ("no_answer", "contacted"):
                ReceptionContactAttempt.objects.create(request=item, cycle=item.contact_cycle, actor=actor,
                    created_at=now, outcome=action, note=reason)
                if item.contact_started_at is None:
                    item.contact_started_at, item.contact_due_at = now, contact_deadline(item, now)
            else:
                if action == "expired" and not expiry_ready(item, now):
                    raise InvalidTransition("Record unanswered attempts on two working days and wait until the second working day ends.")
                item.state, item.closed_at, item.closure_reason = action, now, reason
        item.revision += 1
        item.full_clean(); item.save()
        write_actor_audit_log(actor=actor, business=business, action=AuditLog.Actions.UPDATE, instance=item,
            metadata={"kind": "medical_follow_up_contact", "revision": item.revision, "state": item.state,
                "outcome": action, "cycle": item.contact_cycle, "reason": reason,
                "previous_appointment_id": previous_booking if action == "reopen" else None})
        from .reception_notifications import notify_reception
        notify_reception(item, "changed")
        return CRMCommandResult(data={}, resource=item)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.reception.contact",
        idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business_id),
        payload={"request": request_id, "revision": expected_revision, "action": action, "reason": reason}, operation=operation)
    item.refresh_from_db()
    return item, result.replayed

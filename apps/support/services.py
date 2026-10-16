"""Case commands: access, mutable state, history and audit form one transaction."""
from django.db import transaction
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.audit import write_actor_audit_log
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from apps.core.models import AuditLog
from apps.support.access import active_platform_users, get_case, get_case_business
from apps.support.models import CaseEvent, PublicMessage, SupportCase


class SupportVersionConflict(InvalidTransition):
    error_code = "support_version_conflict"
    default_code = error_code
    default_detail = "The case has changed. Refresh it before retrying."


def clean_text(value, field, maximum, *, required=True):
    if not isinstance(value, str):
        raise ValidationError({field: "Enter text."})
    value = value.strip()
    if (required and not value) or len(value) > maximum:
        raise ValidationError({field: f"Enter between {1 if required else 0} and {maximum} characters."})
    return value


def require_key(key):
    if not isinstance(key, str) or not key.strip() or len(key.strip()) > 128:
        raise ValidationError({"idempotency_key": "A unique Idempotency-Key of at most 128 characters is required."})
    return key.strip()


def audit_case(actor, case, kind, **metadata):
    # Bodies/reasons are only in the scoped support tables, never global audit.
    write_actor_audit_log(
        actor=actor, action=AuditLog.Actions.CREATE if kind == "created" else AuditLog.Actions.UPDATE,
        instance=case, business=case.business,
        metadata={"kind": "support_case", "event": kind, **metadata},
    )


def create_case(*, actor, business_id, subject, text, idempotency_key, platform=False, incident=None, requester_id=None):
    business = get_case_business(actor, business_id, platform=platform)
    if (incident is not None or requester_id is not None) and not platform:
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied()
    subject = clean_text(subject, "subject", 200)
    text = clean_text(text, "text", 6000)
    key = require_key(idempotency_key)
    source = SupportCase.Sources.PLATFORM if platform else SupportCase.Sources.CLINIC

    def perform():
        current_business = get_case_business(actor, business_id, platform=platform)
        # Manual creation records the actual platform author, not an impersonation.
        requester = current_business.owner if platform else actor
        if requester_id is not None:
            from apps.businesses.models import BusinessMember
            requester = get_object_or_404(get_user_model(), pk=requester_id, is_active=True)
            if requester.is_platform_user or not (current_business.owner_id == requester.pk or BusinessMember.objects.filter(
                business=current_business, user=requester, is_active=True).exists()):
                raise ValidationError({"requester_id": "Select an active participant of this business."})
        if not requester.is_active:
            raise ValidationError({"business": "The business owner account is inactive."})
        case = SupportCase.objects.create(
            business=current_business, created_by=actor, requester=requester,
            subject=subject, source=source, last_public_message_at=timezone.now(),
        )
        PublicMessage.objects.create(case=case, author=actor, text=text, source=source)
        CaseEvent.objects.create(case=case, actor=actor, kind=CaseEvent.Kinds.CREATED)
        audit_case(actor, case, "created", source=source)
        if incident is not None:
            from apps.support.incidents import link_incident
            link_incident(actor=actor, case_id=case.pk, business_id=business_id, **incident)
        return CRMCommandResult(data={"case_id": case.pk}, status_code=201, resource=case)

    return run_idempotent_crm_command(
        business=business, actor=actor, action=f"support.create.{source}",
        idempotency_key=key, payload={"subject": subject, "text": text, **({"incident": incident} if incident is not None else {}),
            **({"requester_id": requester_id} if requester_id is not None else {})}, operation=perform,
    )


def change_version(case, expected_version, **changes):
    if isinstance(expected_version, bool) or not isinstance(expected_version, int) or expected_version < 1:
        raise ValidationError({"version": "A positive case version is required."})
    if case.version != expected_version:
        raise SupportVersionConflict()
    updated = SupportCase.objects.filter(pk=case.pk, version=expected_version).update(
        version=F("version") + 1, updated_at=timezone.now(), **changes,
    )
    if updated != 1:
        raise SupportVersionConflict()
    case.refresh_from_db()


@transaction.atomic
def assign_case(*, actor, case_id, assignee_id, version):
    case = get_case(actor, case_id, platform=True, lock=True)
    assignee = None
    if assignee_id is not None:
        assignee = active_platform_users().filter(pk=assignee_id).first()
        if assignee is None:
            raise ValidationError({"assigned_to": "Select an active platform employee."})
    old_id = case.assigned_to_id
    change_version(case, version, assigned_to=assignee)
    CaseEvent.objects.create(
        case=case, actor=actor, kind=CaseEvent.Kinds.ASSIGNED,
        old_value=str(old_id or ""), new_value=str(assignee_id or ""),
    )
    audit_case(actor, case, "assigned", old_assignee=old_id, new_assignee=assignee_id)
    return case


TRANSITIONS = {
    "new": {"in_progress", "resolved"},
    "in_progress": {"waiting_clinic", "waiting_internal", "resolved"},
    "waiting_clinic": {"in_progress", "resolved"},
    "waiting_internal": {"in_progress", "resolved"},
    "resolved": set(),
}


@transaction.atomic
def transition_case(*, actor, case_id, status, reason, version):
    case = get_case(actor, case_id, platform=True, lock=True)
    if status not in SupportCase.Statuses.values:
        raise ValidationError({"status": "Select a valid status."})
    if status not in TRANSITIONS[case.status]:
        raise InvalidTransition()
    reason = clean_text(reason, "reason", 4000, required=status == SupportCase.Statuses.RESOLVED)
    old_status = case.status
    change_version(case, version, status=status, resolved_at=timezone.now() if status == "resolved" else None)
    CaseEvent.objects.create(
        case=case, actor=actor, kind=CaseEvent.Kinds.TRANSITIONED,
        old_value=old_status, new_value=status, reason=reason,
    )
    audit_case(actor, case, "transitioned", old_status=old_status, new_status=status)
    return case


@transaction.atomic
def reopen_case(*, actor, case_id, reason, version, platform=False):
    case = get_case(actor, case_id, platform=platform, lock=True)
    reason = clean_text(reason, "reason", 4000)
    if case.status != SupportCase.Statuses.RESOLVED:
        raise InvalidTransition()
    change_version(case, version, status=SupportCase.Statuses.IN_PROGRESS, resolved_at=None)
    CaseEvent.objects.create(
        case=case, actor=actor, kind=CaseEvent.Kinds.REOPENED,
        old_value="resolved", new_value="in_progress", reason=reason,
    )
    audit_case(actor, case, "reopened")
    return case

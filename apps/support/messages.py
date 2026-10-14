"""Immutable public/private append operations and monotonic public read cursors."""
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from apps.support.access import get_case
from apps.support.models import InternalNote, PublicMessage, ReadState, SupportCase
from apps.support.services import audit_case, clean_text, require_key


def append_message(*, actor, case_id, text, idempotency_key, platform=False, internal=False):
    # Private notes can only enter through the explicit platform path.
    if internal and not platform:
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied("Platform support access is required.")
    case = get_case(actor, case_id, platform=platform)
    text = clean_text(text, "text", 6000)
    key = require_key(idempotency_key)
    model = InternalNote if internal else PublicMessage

    def perform():
        locked = get_case(actor, case_id, platform=platform, lock=True)
        fields = {} if internal else {"source": "platform" if platform else "clinic"}
        message = model.objects.create(case=locked, author=actor, text=text, **fields)
        if not internal:
            now = timezone.now()
            SupportCase.objects.filter(pk=locked.pk).update(last_public_message_at=now, updated_at=now)
        # Append-only messages never overwrite each other or change lifecycle.
        # A private note also never changes clinic-visible ordering/version/unread.
        audit_case(actor, locked, "internal_note_added" if internal else "message_added", message_id=message.pk)
        return CRMCommandResult(data={"case_id": locked.pk, "message_id": message.pk}, status_code=201, resource=message)

    return run_idempotent_crm_command(
        business=case.business, actor=actor,
        action=f"support.{case.pk}.{'note' if internal else 'message'}.{'platform' if platform else 'clinic'}",
        idempotency_key=key, payload={"text": text}, operation=perform,
    )


@transaction.atomic
def mark_read(*, actor, case_id, through_id, platform=False):
    case = get_case(actor, case_id, platform=platform, lock=True)
    if isinstance(through_id, bool) or not isinstance(through_id, int) or not PublicMessage.objects.filter(case=case, pk=through_id).exists():
        raise ValidationError({"through_id": "Select a public message from this case."})
    state, _ = ReadState.objects.get_or_create(case=case, user=actor)
    ReadState.objects.filter(pk=state.pk, last_read_message_id__lt=through_id).update(last_read_message_id=through_id)
    state.refresh_from_db()
    return state

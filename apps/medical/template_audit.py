from django.core.exceptions import ValidationError as ModelValidationError
from django.db import DatabaseError

from .audit import MedicalAuditUnavailable
from .models import MedicalAuditEvent, MedicalDocumentTemplateRevision, MedicalTemplateReview


def write_template_audit(*, actor, business, version, action):
    if action not in {"read", "template_draft_created", "template_draft_saved",
                      "template_submitted", "template_approved", "template_rejected"}:
        raise ValueError("Select a template action.")
    current = MedicalDocumentTemplateRevision.objects.select_related("template").filter(
        pk=version.pk, template__business=business).first()
    if current is None:
        raise ValueError("Audit template must belong to this business.")
    try:
        current.template.clean()
    except ModelValidationError:
        raise ValueError("Audit template links must be consistent.") from None
    if current.revision > current.template.revision:
        raise ValueError("Audit template version exceeds the current revision.")
    if action in {"template_draft_created", "template_draft_saved"} and (
            current.revision != current.template.revision or current.author_id != actor.pk):
        raise ValueError("A template write event requires the actor's current version.")
    if action == "template_submitted" and not MedicalTemplateReview.objects.filter(
            version=current, state="pending", submitted_by=actor).exists():
        raise ValueError("Submission audit requires the actor's pending review.")
    if action in {"template_approved", "template_rejected"} and not MedicalTemplateReview.objects.filter(
            version=current, state=action.removeprefix("template_"), decided_by=actor).exists():
        raise ValueError("Decision audit requires the actor's matching review decision.")
    if (action == "template_draft_created" and current.revision != 1) or (
            action == "template_draft_saved" and current.revision <= 1):
        raise ValueError("The template action must match its version.")
    try:
        event = MedicalAuditEvent.objects.create(business=business, actor=actor,
            template_version=current, action=action, result="success")
        if event is None or event.pk is None:
            raise MedicalAuditUnavailable()
        return event
    except DatabaseError:
        raise MedicalAuditUnavailable() from None

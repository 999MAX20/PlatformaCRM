from django.db import transaction
from rest_framework.exceptions import ValidationError

from .audit import write_patient_audit
from .document_artifact_access import document_artifact_access
from .models import MedicalAuditEvent


@transaction.atomic
def list_document_export_history(*, actor, business_id, patient_id, version_id, before_id=None, limit=20, **basis):
    if type(limit) is not int or not 1 <= limit <= 50 or (
            before_id is not None and (type(before_id) is not int or before_id <= 0)):
        raise ValidationError({"page": "Provide a valid history cursor and page size."})
    context = document_artifact_access(actor=actor, business_id=business_id, patient_id=patient_id,
        version_id=version_id, **basis)
    events = MedicalAuditEvent.objects.select_related("actor").filter(business=context.business,
        patient=context.patient, document_version=context.version, result="success",
        action__in=["document_exported", "document_print_requested"])
    if before_id is not None:
        events = events.filter(pk__lt=before_id)
    page = list(events.order_by("-pk")[:limit + 1])
    write_patient_audit(actor=actor, business=context.business, patient=context.patient, action="read",
        document_version=context.version, correction_access=context.correction)
    return {"results": [{"id": event.pk, "action": event.action, "created_at": event.created_at,
                         "actor": {"id": event.actor_id, "name": event.actor.full_name},
                         "version_id": context.version.pk, "revision": context.version.revision}
                        for event in page[:limit]],
            "next_before_id": page[limit - 1].pk if len(page) > limit else None}

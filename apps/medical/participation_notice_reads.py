from django.db import transaction
from rest_framework.exceptions import NotFound, ValidationError

from apps.notifications.personal_selectors import personal_states
from .models import MedicalParticipationNotice, MedicalRoleAssignment
from .participation_notifications import REPLIES
from .participation_reads import _context, _page, _rows


@transaction.atomic
def read_participation_notification(*, actor, business_id, notification_id):
    if type(notification_id) is not int or notification_id <= 0:
        raise ValidationError({"notification_id": "Provide a valid notification identifier."})
    business, role = _context(actor, business_id, None, 20)
    states = personal_states(actor=actor, business=business).filter(notification_id=notification_id)
    notice = MedicalParticipationNotice.objects.select_related("event__participation").filter(
        notification_id__in=states.values("notification_id")).first()
    if notice is None:
        raise NotFound()
    item = notice.event.participation
    page = _page(actor, business, _rows(business).filter(pk=item.pk), None, 1)
    if not page["results"]:
        raise NotFound()
    outgoing = notice.event.action in REPLIES
    doctor_source = outgoing and role.kind == MedicalRoleAssignment.Kinds.DOCTOR
    return {"participation": page["results"][0], "direction": "outgoing" if outgoing else "incoming",
        "source_appointment_id": item.source_appointment_id if doctor_source else None,
        "source_participation_id": item.source_participation_id if doctor_source else None}

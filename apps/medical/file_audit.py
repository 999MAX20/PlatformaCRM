from django.db import DatabaseError, transaction
from django.db.models import Q

from apps.businesses.models import Business
from .audit import MedicalAuditUnavailable
from .models import MedicalAuditEvent


def record_denied_file_access(*, actor, business_id):
    # Never associate a foreign patient's identifiers with the caller's audit scope.
    business = Business.objects.filter(pk=business_id).filter(
        Q(owner=actor) | Q(members__user=actor, members__is_active=True)).distinct().first()
    if business is None:
        return
    try:
        with transaction.atomic():
            event = MedicalAuditEvent.objects.create(business=business, actor=actor,
                action="access_denied", result="denied")
            if event is None or event.pk is None:
                raise MedicalAuditUnavailable()
    except DatabaseError:
        raise MedicalAuditUnavailable() from None

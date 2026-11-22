from django.db import transaction
from django.db.models import Exists, OuterRef
from rest_framework.exceptions import ValidationError

from apps.businesses.access import Resources
from apps.clients.models import Client
from apps.core.crm_read_scope import readable_queryset
from .audit import write_patient_audit
from .models import DentalMedicalRecord
from .patient_search import _scope_audit
from .patient_selectors import reception_context


@transaction.atomic
def patient_list_projection(*, actor, business_id, branch_id, client_ids):
    actor, business, _ = reception_context(actor=actor, business_id=business_id, branch_id=branch_id, action="view")
    if not isinstance(client_ids, list) or not 1 <= len(client_ids) <= 100 or any(type(pk) is not int or pk <= 0 for pk in client_ids):
        raise ValidationError({"client_ids": "Provide between 1 and 100 client identifiers."})
    clients = readable_queryset(Client.objects.filter(pk__in=client_ids), actor=actor, business=business, resource=Resources.CLIENTS)
    clients = clients.select_related("medical_profile").annotate(has_record=Exists(
        DentalMedicalRecord.objects.filter(business=business, patient__client_id=OuterRef("pk"))))
    _scope_audit(actor, business)
    results = []
    for client in clients.order_by("pk"):
        patient = getattr(client, "medical_profile", None)
        if patient is not None:
            if patient.business_id != business.pk:
                continue
            write_patient_audit(actor=actor, business=business, patient=patient, action="read")
        results.append({"client_id": client.pk, "has_record": client.has_record,
                        "identity_status": patient.identity_status if patient else None})
    return {"results": results}

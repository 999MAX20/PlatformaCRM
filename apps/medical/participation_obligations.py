from apps.scheduling.models import Appointment, Resource
from .models import MedicalEncounter
from .encounter_completion_requirements import encounter_document_requirements


def participation_obligations(*, business, patient, member, limit=50, offset=0):
    """No mutation: enumerate the clinician's remaining work for this patient."""
    appointments = Appointment.objects.filter(
        business=business, client_id=patient.client_id, client__business=business,
        resource__business=business, resource__resource_type=Resource.ResourceTypes.STAFF,
        resource__linked_user_id=member.user_id, is_archived=False,
    ).exclude(status__in=(Appointment.Statuses.COMPLETED, Appointment.Statuses.CANCELLED,
                         Appointment.Statuses.NO_SHOW))
    encounters = MedicalEncounter.objects.filter(
        business=business, patient=patient, primary_clinician=member,
    ).exclude(state=MedicalEncounter.States.FINALIZED)
    documents = []
    for encounter in MedicalEncounter.objects.filter(business=business, patient=patient,
            primary_clinician=member).select_related("appointment").order_by("pk"):
        for document in encounter_document_requirements(encounter,
                required_moments={"before_treatment", "before_completion", "before_issue"}):
            if not document["ready"]:
                documents.append({**document, "encounter_id": encounter.pk, "appointment_id": encounter.appointment_id})
    return {
        "documents": {"count": len(documents), "items": documents[offset:offset + limit]},
        "appointments": {"count": appointments.count(), "ids": list(appointments.order_by("pk").values_list("pk", flat=True)[offset:offset + limit])},
        "encounters": {"count": encounters.count(), "ids": list(encounters.order_by("pk").values_list("pk", flat=True)[offset:offset + limit])},
    }

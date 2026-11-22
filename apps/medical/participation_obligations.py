from apps.scheduling.models import Appointment, Resource
from .models import MedicalEncounter


def participation_obligations(*, business, patient, member, limit=50):
    """Existing encounter/booking obligations; document lifecycle adds its own source."""
    appointments = Appointment.objects.filter(
        business=business, client_id=patient.client_id, client__business=business,
        resource__business=business, resource__resource_type=Resource.ResourceTypes.STAFF,
        resource__linked_user_id=member.user_id, is_archived=False,
    ).exclude(status__in=(Appointment.Statuses.COMPLETED, Appointment.Statuses.CANCELLED,
                         Appointment.Statuses.NO_SHOW))
    encounters = MedicalEncounter.objects.filter(
        business=business, patient=patient, primary_clinician=member,
    ).exclude(state=MedicalEncounter.States.FINALIZED)
    return {
        "appointments": {"count": appointments.count(), "ids": list(appointments.order_by("pk").values_list("pk", flat=True)[:limit])},
        "encounters": {"count": encounters.count(), "ids": list(encounters.order_by("pk").values_list("pk", flat=True)[:limit])},
    }

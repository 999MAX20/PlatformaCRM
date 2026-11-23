from apps.core.domain_errors import InvalidTransition
from apps.businesses.capabilities import is_module_enabled
from .models import MedicalEncounter


def validate_appointment_transition(*, appointment, actor, target):
    if target != "completed":
        return
    encounter = MedicalEncounter.objects.filter(appointment=appointment).first()
    if encounter is None and is_module_enabled(appointment.business, "medical_records"):
        raise InvalidTransition("Open and complete the clinical encounter first.",
            errors={"medical_encounter": "clinical_encounter_required"})
    if encounter is not None and encounter.state != "finalized":
        raise InvalidTransition("Complete the clinical encounter before completing this appointment.",
            errors={"medical_encounter": "clinical_completion_required"})

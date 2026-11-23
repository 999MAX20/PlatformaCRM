from django.db import transaction

from .audit import write_patient_audit
from .encounter_reads import _clinical_read_context, _encounter_summary
from .models import DentalMedicalRecord, MedicalEncounter
from .patient_selectors import patient_demographics


@transaction.atomic
def read_clinical_overview(*, actor, business_id, patient_id, appointment_id=None, participation_id=None):
    scope = dict(actor=actor, business_id=business_id, patient_id=patient_id,
                 appointment_id=appointment_id, participation_id=participation_id)
    business, patient = _clinical_read_context(**scope)
    record = DentalMedicalRecord.objects.filter(business=business, patient=patient, state="active").first()
    write_patient_audit(actor=actor, business=business, patient=patient, action="read", record=record)
    demographics = patient_demographics(patient) if patient.demographics_encrypted else {}
    latest = MedicalEncounter.objects.select_related("branch", "primary_clinician__user").filter(
        business=business, patient=patient).order_by("-started_at", "-pk").first()
    return {"patient_id": patient.pk, "patient_revision": patient.revision,
            "full_name": patient.client.full_name, "identity_status": patient.identity_status,
            "date_of_birth": demographics.get("date_of_birth"),
            "active_record": {"id": record.pk, "number": record.number, "opened_at": record.opened_at} if record else None,
            "latest_encounter": _encounter_summary(actor=actor, business=business, patient=patient,
                encounter=latest) if latest else None}

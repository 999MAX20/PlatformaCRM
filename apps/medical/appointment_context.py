from django.db import transaction
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.businesses.models import Business
from apps.core.domain_errors import InvalidTransition
from .appointment_access import assert_assigned_medical_appointment
from .audit import write_patient_audit
from .clinical_identity import assert_verified_clinical_identity
from .identity_crypto import MedicalDataUnavailable
from .models import DentalMedicalRecord, MedicalEncounter, MedicalEncounterRevision, PatientProfile
from .role_access import assert_medical_branch_permission


@transaction.atomic
def read_appointment_clinical_context(*, actor, business_id, appointment_id):
    if any(type(value) is not int or value <= 0 for value in (business_id, appointment_id)):
        raise ValidationError({"appointment": "Provide valid business and appointment identifiers."})
    business = Business.objects.select_for_update().filter(pk=business_id).first()
    if business is None:
        raise NotFound()
    appointment, context = assert_assigned_medical_appointment(actor=actor, business=business, appointment_id=appointment_id)
    patient = PatientProfile.objects.select_for_update().filter(business=business, client_id=appointment.client_id).first()
    if patient is None:
        raise NotFound()
    record = DentalMedicalRecord.objects.filter(business=business, patient=patient, state="active").first()
    encounter = MedicalEncounter.objects.filter(business=business, patient=patient, appointment=appointment).first()
    write_patient_audit(actor=actor, business=business, patient=patient, action="read", record=record)
    version = None
    if encounter:
        version = MedicalEncounterRevision.objects.filter(encounter=encounter, revision=encounter.revision).first()
        if version is None:
            raise MedicalDataUnavailable()
        write_patient_audit(actor=actor, business=business, patient=patient, action="read", encounter_version=version)
    verified = True
    try:
        assert_verified_clinical_identity(patient)
    except InvalidTransition:
        verified = False

    def allowed(action):
        try:
            assert_medical_branch_permission(actor, business, "medical_records", action, branch=appointment.branch)
        except PermissionDenied:
            return False
        return verified

    can_create, can_update = allowed("create"), allowed("update")
    return {"business_id": business.pk,
        "patient": {"id": patient.pk, "client_id": patient.client_id, "full_name": appointment.client.full_name,
            "revision": patient.revision, "identity_status": patient.identity_status},
        "appointment": {"id": appointment.pk, "updated_at": appointment.updated_at, "branch_id": appointment.branch_id,
            "start_at": appointment.start_at, "end_at": appointment.end_at},
        "active_record": {"id": record.pk, "number": record.number, "opened_at": record.opened_at} if record else None,
        "encounter": {"id": encounter.pk, "revision": encounter.revision, "state": encounter.state,
            "version_id": version.pk} if encounter else None,
        "actions": {"create_record": can_create and record is None,
            "open_encounter": can_create and record is not None and encounter is None,
            "save_draft": bool(can_update and record and encounter and encounter.state == "draft" and
                               encounter.primary_clinician_id == context.member_id and encounter.record_id == record.pk)}}

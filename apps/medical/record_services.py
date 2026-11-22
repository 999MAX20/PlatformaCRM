from django.db import transaction
from rest_framework.exceptions import NotFound, ValidationError

from apps.businesses.models import Business
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from .appointment_access import assert_appointment_medical_basis
from .audit import write_patient_audit
from .clinical_identity import assert_verified_clinical_identity
from .identity_crypto import medical_request_digest
from .models import DentalMedicalRecord, PatientProfile
from .participation_access import assert_treatment_medical_basis
from .role_access import assert_medical_role_permission


@transaction.atomic
def open_dental_record(*, actor, business_id, patient_id, number, expected_patient_revision,
                       idempotency_key, appointment_id=None, participation_id=None):
    if (appointment_id is None) == (participation_id is None):
        raise ValidationError({"basis": "Select one treatment access basis."})
    ids = [business_id, patient_id, expected_patient_revision,
           appointment_id if appointment_id is not None else participation_id]
    if any(type(value) is not int or value <= 0 for value in ids):
        raise ValidationError({"record": "Provide valid identifiers and revision."})
    if not isinstance(number, str) or not number.strip() or len(number) > 64:
        raise ValidationError({"number": "Provide a local record number of at most 64 characters."})
    number = number.strip()
    if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 128:
        raise ValidationError({"idempotency_key": "Provide an idempotency key of at most 128 characters."})
    business = Business.objects.select_for_update().filter(pk=business_id).first()
    if business is None:
        raise NotFound()
    assert_medical_role_permission(actor, business, "medical_records", "create")
    patient = PatientProfile.objects.select_for_update().filter(pk=patient_id,
        business=business, client__business_id=business_id).first()
    if patient is None:
        raise NotFound()
    if appointment_id is not None:
        assert_appointment_medical_basis(actor=actor, business=business, patient_id=patient_id,
            appointment_id=appointment_id, action="create")
    else:
        assert_treatment_medical_basis(actor=actor, business=business, patient_id=patient_id,
            participation_id=participation_id, action="create")

    assert_verified_clinical_identity(patient)

    def operation():
        if patient.revision != expected_patient_revision:
            raise InvalidTransition("Patient changed; review the current profile.")
        if DentalMedicalRecord.objects.filter(business=business, patient=patient, state="active").exists():
            raise InvalidTransition("This patient already has an active medical record.")
        if DentalMedicalRecord.objects.filter(business=business, number=number).exists():
            raise InvalidTransition("This local medical record number is unavailable.")
        record = DentalMedicalRecord(business=business, patient=patient, number=number, opened_by=actor)
        record.full_clean()
        record.save(force_insert=True)
        write_patient_audit(actor=actor, business=business, patient=patient, action="record_opened", record=record)
        return CRMCommandResult(data={}, status_code=201, resource=record)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.record.open",
        idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business_id),
        payload={"patient": patient_id, "patient_revision": expected_patient_revision,
            "appointment": appointment_id, "participation": participation_id,
            "number_digest": medical_request_digest({"number": number}, business_id=business_id)}, operation=operation)
    record = DentalMedicalRecord.objects.get(business=business, patient=patient,
        pk=result.resource_id if result.replayed else result.resource.pk)
    return record, result.replayed

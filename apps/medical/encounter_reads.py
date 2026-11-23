from django.db import transaction
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.businesses.models import Business
from .appointment_access import assert_appointment_medical_basis
from .audit import write_patient_audit
from .encounter_content import read_encounter_revision
from .identity_crypto import MedicalDataUnavailable
from .models import DentalMedicalRecord, MedicalEncounter, MedicalEncounterRevision, PatientProfile
from .participation_access import assert_treatment_medical_basis
from .role_access import assert_medical_role_permission


def _clinical_read_context(*, actor, business_id, patient_id, appointment_id, participation_id):
    if (appointment_id is None) == (participation_id is None):
        raise ValidationError({"basis": "Select one current treatment access basis."})
    ids = [business_id, patient_id,
           appointment_id if appointment_id is not None else participation_id]
    if any(type(value) is not int or value <= 0 for value in ids):
        raise ValidationError({"encounter": "Provide valid identifiers."})
    business = Business.objects.select_for_update().filter(pk=business_id).first()
    if business is None:
        raise NotFound()
    assert_medical_role_permission(actor, business, "medical_records", "view")
    patient = PatientProfile.objects.select_for_update().filter(pk=patient_id,
        business=business, client__business_id=business_id).first()
    if patient is None:
        raise NotFound()
    if appointment_id is not None:
        assert_appointment_medical_basis(actor=actor, business=business, patient_id=patient_id,
            appointment_id=appointment_id)
    else:
        assert_treatment_medical_basis(actor=actor, business=business, patient_id=patient_id,
            participation_id=participation_id)
    return business, patient


@transaction.atomic
def read_encounter_for_treating_clinician(*, actor, business_id, patient_id, version_id,
                                        appointment_id=None, participation_id=None):
    if type(version_id) is not int or version_id <= 0:
        raise ValidationError({"version_id": "Provide a valid version identifier."})
    business, patient = _clinical_read_context(actor=actor, business_id=business_id, patient_id=patient_id,
        appointment_id=appointment_id, participation_id=participation_id)
    version = MedicalEncounterRevision.objects.select_related("encounter", "author").filter(pk=version_id,
        encounter__patient=patient, encounter__business=business).first()
    if version is None:
        raise PermissionDenied()
    write_patient_audit(actor=actor, business=business, patient=patient, action="read", encounter_version=version)
    clinical = read_encounter_revision(version)
    return {"version_id": version.pk, "encounter_id": version.encounter_id, "revision": version.revision,
        "author_id": version.author_id, "author_name": version.author.full_name,
        "created_at": version.created_at, **clinical}


@transaction.atomic
def read_clinical_workspace(*, actor, business_id, patient_id, appointment_id=None,
                            participation_id=None, before_id=None, limit=20,
                            branch_id=None, author_id=None, state=None, date_from=None, date_to=None):
    from .encounter_filters import encounter_filter_options, filter_encounters
    if type(limit) is not int or not 1 <= limit <= 50 or (
            before_id is not None and (type(before_id) is not int or before_id <= 0)):
        raise ValidationError({"pagination": "Select a limit from 1 to 50 and a valid cursor."})
    business, patient = _clinical_read_context(actor=actor, business_id=business_id, patient_id=patient_id,
        appointment_id=appointment_id, participation_id=participation_id)
    record = DentalMedicalRecord.objects.filter(business=business, patient=patient, state="active").first()
    write_patient_audit(actor=actor, business=business, patient=patient, action="read", record=record)
    encounters = MedicalEncounter.objects.select_related("branch", "primary_clinician__user").filter(
        business=business, patient=patient).order_by("-pk")
    options = encounter_filter_options(encounters, business=business)
    encounters = filter_encounters(encounters, branch_id=branch_id, author_id=author_id,
        state=state, date_from=date_from, date_to=date_to)
    if before_id is not None:
        encounters = encounters.filter(pk__lt=before_id)
    page = list(encounters[:limit + 1])
    rows = [_encounter_summary(actor=actor, business=business, patient=patient, encounter=encounter)
            for encounter in page[:limit]]
    return {"patient_id": patient.pk, "patient_revision": patient.revision, "identity_status": patient.identity_status,
        "active_record": {"id": record.pk, "number": record.number, "opened_at": record.opened_at} if record else None,
        "encounters": rows, "next_before_id": rows[-1]["id"] if len(page) > limit else None,
        "filter_options": options}


def _encounter_summary(*, actor, business, patient, encounter):
    if (encounter.branch.business_id != business.pk or
            encounter.primary_clinician.business_id != business.pk):
        raise MedicalDataUnavailable()
    version = MedicalEncounterRevision.objects.select_related("author").filter(
        encounter=encounter, revision=encounter.revision).only(
        "id", "encounter_id", "revision", "author_id", "author__full_name", "created_at").first()
    if version is None:
        raise MedicalDataUnavailable()
    write_patient_audit(actor=actor, business=business, patient=patient, action="read", encounter_version=version)
    return {"id": encounter.pk, "record_id": encounter.record_id, "appointment_id": encounter.appointment_id,
        "branch_id": encounter.branch_id, "primary_clinician_id": encounter.primary_clinician_id,
        "branch_name": encounter.branch.name, "primary_clinician_name": encounter.primary_clinician.user.full_name,
        "started_at": encounter.started_at, "ended_at": encounter.ended_at, "state": encounter.state,
        "revision": encounter.revision, "version_id": version.pk, "author_id": version.author_id,
        "author_name": version.author.full_name}


@transaction.atomic
def read_encounter_history(*, actor, business_id, patient_id, encounter_id, appointment_id=None,
                           participation_id=None, before_revision=None, limit=20):
    if type(encounter_id) is not int or encounter_id <= 0 or type(limit) is not int or not 1 <= limit <= 50 or (
            before_revision is not None and (type(before_revision) is not int or before_revision <= 0)):
        raise ValidationError({"history": "Provide a valid encounter, cursor and limit from 1 to 50."})
    business, patient = _clinical_read_context(actor=actor, business_id=business_id, patient_id=patient_id,
        appointment_id=appointment_id, participation_id=participation_id)
    encounter = MedicalEncounter.objects.filter(pk=encounter_id, business=business, patient=patient).first()
    if encounter is None:
        raise PermissionDenied()
    versions = MedicalEncounterRevision.objects.select_related("author").filter(encounter=encounter).only(
        "id", "encounter_id", "revision", "author_id", "author__full_name", "created_at")
    current = versions.filter(revision=encounter.revision).first()
    if current is None:
        raise MedicalDataUnavailable()
    history = versions.filter(revision__lte=encounter.revision).order_by("-revision")
    if before_revision is not None:
        history = history.filter(revision__lt=before_revision)
    page = list(history[:limit + 1])
    exposed = {version.pk: version for version in [current, *page[:limit]]}
    for version in exposed.values():
        write_patient_audit(actor=actor, business=business, patient=patient, action="read", encounter_version=version)
    rows = [{"version_id": version.pk, "revision": version.revision, "author_id": version.author_id,
             "author_name": version.author.full_name, "created_at": version.created_at} for version in page[:limit]]
    return {"encounter_id": encounter.pk, "current_revision": encounter.revision, "state": encounter.state,
        "versions": rows, "next_before_revision": rows[-1]["revision"] if len(page) > limit else None}

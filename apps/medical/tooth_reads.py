from datetime import datetime

from django.db import transaction
from django.db.models import OuterRef, Subquery
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from .audit import write_patient_audit
from .encounter_reads import _clinical_read_context
from .identity_crypto import MedicalDataUnavailable
from .models import DentalToothHistory, DentalToothState, FDI_TOOTH_NUMBERS
from .tooth_policy import configured_surface_policy
from .tooth_content import read_tooth_history


@transaction.atomic
def read_tooth_observation(*, actor, business_id, patient_id, history_id,
                           appointment_id=None, participation_id=None):
    if type(history_id) is not int or history_id <= 0:
        raise ValidationError({"history_id": "Provide a valid observation identifier."})
    business, patient = _clinical_read_context(actor=actor, business_id=business_id, patient_id=patient_id,
        appointment_id=appointment_id, participation_id=participation_id)
    history = DentalToothHistory.objects.select_related("tooth_state", "encounter", "author").filter(pk=history_id,
        tooth_state__business=business, tooth_state__patient=patient, encounter__business=business,
        encounter__patient=patient).first()
    if history is None:
        raise PermissionDenied()
    return _audited_content(actor, business, patient, history)


def _audited_content(actor, business, patient, history):
    write_patient_audit(actor=actor, business=business, patient=patient, action="read", tooth_history=history)
    content = read_tooth_history(history)
    return {"history_id": history.pk, "tooth_state_id": history.tooth_state_id,
        "tooth": history.tooth_state.tooth, "surface": history.tooth_state.surface,
        "revision": history.revision, "previous_id": history.previous_id, "encounter_id": history.encounter_id,
        "author_id": history.author_id, "author_name": history.author.full_name,
        "observed_at": history.observed_at, "created_at": history.created_at, **content}


def _page_values(limit, cursor):
    if type(limit) is not int or not 1 <= limit <= 50 or (
            cursor is not None and (type(cursor) is not int or cursor <= 0)):
        raise ValidationError({"pagination": "Provide a limit from 1 to 50 and a positive cursor."})


@transaction.atomic
def read_tooth_snapshot(*, actor, business_id, patient_id, appointment_id=None,
                        participation_id=None, as_of=None, after_state_id=None, limit=50):
    _page_values(limit, after_state_id)
    if as_of is not None and (not isinstance(as_of, datetime) or timezone.is_naive(as_of)):
        raise ValidationError({"as_of": "Provide a timestamp with timezone."})
    business, patient = _clinical_read_context(actor=actor, business_id=business_id, patient_id=patient_id,
        appointment_id=appointment_id, participation_id=participation_id)
    cutoff = as_of or timezone.now()
    latest = DentalToothHistory.objects.filter(tooth_state_id=OuterRef("pk"), observed_at__lte=cutoff).order_by(
        "-observed_at", "-revision")
    states = DentalToothState.objects.filter(business=business, patient=patient).annotate(
        selected_id=Subquery(latest.values("pk")[:1])).order_by("pk")
    if after_state_id is not None:
        states = states.filter(pk__gt=after_state_id)
    # Page locations even when their first observation is later than the cutoff.
    page = list(states[:limit + 1])
    write_patient_audit(actor=actor, business=business, patient=patient, action="read")
    rows = []
    for state in page[:limit]:
        if not DentalToothHistory.objects.filter(tooth_state=state, revision=state.revision).exists():
            raise MedicalDataUnavailable()
        if state.selected_id is None:
            continue
        history = DentalToothHistory.objects.select_related("tooth_state", "encounter", "author").get(pk=state.selected_id)
        if history.encounter.business_id != business.pk or history.encounter.patient_id != patient.pk:
            raise MedicalDataUnavailable()
        row = _audited_content(actor, business, patient, history)
        rows.append({**row, "current_revision": state.revision})
    return {"as_of": cutoff, "observations": rows,
        "next_after_state_id": page[limit - 1].pk if len(page) > limit else None}


@transaction.atomic
def read_tooth_revision_history(*, actor, business_id, patient_id, tooth_state_id,
                               appointment_id=None, participation_id=None, before_revision=None, limit=20):
    _page_values(limit, before_revision)
    if type(tooth_state_id) is not int or tooth_state_id <= 0:
        raise ValidationError({"tooth_state_id": "Provide a valid location identifier."})
    business, patient = _clinical_read_context(actor=actor, business_id=business_id, patient_id=patient_id,
        appointment_id=appointment_id, participation_id=participation_id)
    state = DentalToothState.objects.filter(pk=tooth_state_id, business=business, patient=patient).first()
    if state is None:
        raise PermissionDenied()
    versions = DentalToothHistory.objects.select_related("tooth_state", "encounter", "author").filter(tooth_state=state)
    current = versions.filter(revision=state.revision).first()
    if current is None:
        raise MedicalDataUnavailable()
    versions = versions.filter(revision__lte=state.revision).order_by("-revision")
    if before_revision is not None:
        versions = versions.filter(revision__lt=before_revision)
    page = list(versions[:limit + 1])
    for history in {item.pk: item for item in [current, *page[:limit]]}.values():
        write_patient_audit(actor=actor, business=business, patient=patient, action="read", tooth_history=history)
    rows = [{"history_id": item.pk, "revision": item.revision, "previous_id": item.previous_id,
        "encounter_id": item.encounter_id, "encounter_state": item.encounter.state,
        "author_id": item.author_id, "author_name": item.author.full_name,
        "observed_at": item.observed_at, "created_at": item.created_at} for item in page[:limit]]
    return {"tooth_state_id": state.pk, "tooth": state.tooth, "surface": state.surface,
        "current_revision": state.revision, "versions": rows,
        "next_before_revision": rows[-1]["revision"] if len(page) > limit else None}


@transaction.atomic
def read_tooth_surface_options(*, actor, business_id, patient_id, tooth,
                              appointment_id=None, participation_id=None):
    if type(tooth) is not int or tooth not in FDI_TOOTH_NUMBERS:
        raise ValidationError({"tooth": "Select a valid tooth number."})
    business, patient = _clinical_read_context(actor=actor, business_id=business_id, patient_id=patient_id,
        appointment_id=appointment_id, participation_id=participation_id)
    policy = configured_surface_policy(business.pk)
    write_patient_audit(actor=actor, business=business, patient=patient, action="read")
    codes = policy["teeth"].get(str(tooth), []) if policy else []
    return {"tooth": tooth, "configured": policy is not None,
        "reference": policy["reference"] if policy else None,
        "surfaces": [{"code": code, "labels": dict(policy.get("labels", {}).get(code, {}))} for code in codes]}

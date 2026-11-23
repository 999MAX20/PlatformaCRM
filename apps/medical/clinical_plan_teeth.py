from datetime import datetime

from django.db import transaction
from django.db.models import OuterRef, Subquery, F
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .audit import write_patient_audit
from .encounter_reads import _clinical_read_context
from .identity_crypto import MedicalDataUnavailable
from .models import FDI_TOOTH_NUMBERS, MedicalEncounterRevision, MedicalPlanToothLink


def _references(content):
    return {(step["id"], tooth) for step in content.get("plan_steps", []) for tooth in step.get("teeth", [])}


def store_plan_teeth(*, version, content):
    # Descending cursor IDs retain the clinical step order within each version.
    MedicalPlanToothLink.objects.bulk_create([MedicalPlanToothLink(version=version, step_id=step["id"], tooth=tooth)
        for step in reversed(content.get("plan_steps", [])) for tooth in step.get("teeth", [])])


def verify_plan_teeth(*, version, content):
    actual = {(str(key), tooth) for key, tooth in version.plan_tooth_links.values_list("step_id", "tooth")}
    if actual != _references(content):
        raise MedicalDataUnavailable()


@transaction.atomic
def read_tooth_plan_steps(*, actor, business_id, patient_id, tooth, appointment_id=None,
                         participation_id=None, as_of=None, before_id=None, limit=20):
    if type(tooth) is not int or tooth not in FDI_TOOTH_NUMBERS:
        raise ValidationError({"tooth": "Select a permanent or primary FDI tooth number."})
    if type(limit) is not int or not 1 <= limit <= 50 or (
            before_id is not None and (type(before_id) is not int or before_id <= 0)):
        raise ValidationError({"pagination": "Provide a limit from 1 to 50 and a positive cursor."})
    if as_of is not None and (not isinstance(as_of, datetime) or timezone.is_naive(as_of)):
        raise ValidationError({"as_of": "Provide a timestamp with timezone."})
    business, patient = _clinical_read_context(actor=actor, business_id=business_id, patient_id=patient_id,
        appointment_id=appointment_id, participation_id=participation_id)
    cutoff = as_of or timezone.now()
    latest = MedicalEncounterRevision.objects.filter(encounter_id=OuterRef("version__encounter_id"),
        created_at__lte=cutoff, revision__lte=F("encounter__revision")).order_by("-revision")
    query = MedicalPlanToothLink.objects.filter(tooth=tooth, version__encounter__business=business,
        version__encounter__patient=patient).annotate(latest_id=Subquery(latest.values("pk")[:1])).filter(
        version_id=F("latest_id")).select_related("version__author", "version__encounter")
    if before_id is not None:
        query = query.filter(pk__lt=before_id)
    page = list(query.order_by("-pk")[:limit + 1])
    write_patient_audit(actor=actor, business=business, patient=patient, action="read")
    from .encounter_content import read_encounter_revision
    versions = {}
    rows = []
    for link in page[:limit]:
        version = link.version
        if version.pk not in versions:
            write_patient_audit(actor=actor, business=business, patient=patient, action="read", encounter_version=version)
            versions[version.pk] = read_encounter_revision(version)["content"]
        step = next((item for item in versions[version.pk].get("plan_steps", []) if item["id"] == str(link.step_id)), None)
        if step is None or tooth not in step.get("teeth", []):
            raise MedicalDataUnavailable()
        rows.append({"id": link.pk, "step": step, "version_id": version.pk, "revision": version.revision,
            "encounter_id": version.encounter_id, "author_id": version.author_id,
            "author_name": version.author.full_name, "created_at": version.created_at})
    return {"as_of": cutoff, "results": rows, "next_before_id": page[limit - 1].pk if len(page) > limit else None}

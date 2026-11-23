from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.businesses.models import Business
from apps.scheduling.plan_selectors import readable_plans, readable_plan_steps
from .audit import write_patient_audit
from .clinical_plan_links import patient_visit_steps, visit_step_snapshot
from .encounter_reads import _clinical_read_context
from .models import MedicalEncounter


@transaction.atomic
def list_clinical_visit_steps(*, actor, business_id, patient_id, encounter_id,
                             appointment_id=None, participation_id=None, correction_access_id=None,
                             before_id=None, limit=20):
    identifiers = [business_id, patient_id, encounter_id]
    identifiers += [value for value in (appointment_id, participation_id, correction_access_id, before_id) if value is not None]
    if any(type(value) is not int or value <= 0 for value in identifiers):
        raise ValidationError({"scope": "Provide valid scope identifiers."})
    if sum(value is not None for value in (appointment_id, participation_id, correction_access_id)) != 1:
        raise ValidationError({"basis": "Select one treatment access basis."})
    if type(limit) is not int or not 1 <= limit <= 50:
        raise ValidationError({"limit": "Select a limit from 1 to 50."})
    correction = None
    if correction_access_id is not None:
        from .correction_access_context import assert_correction_access
        business = Business.objects.select_for_update().filter(pk=business_id).first()
        if business is None:
            raise PermissionDenied()
        correction = assert_correction_access(actor=actor, business=business, request_id=correction_access_id,
                                              encounter_id=encounter_id, action="view")
        if correction.patient_id != patient_id or correction.document_id is not None:
            raise PermissionDenied()
        patient = correction.patient
    else:
        business, patient = _clinical_read_context(actor=actor, business_id=business_id, patient_id=patient_id,
            appointment_id=appointment_id, participation_id=participation_id)
    encounter = MedicalEncounter.objects.filter(pk=encounter_id, patient=patient, business=business).first()
    if encounter is None:
        raise PermissionDenied()
    plans = readable_plans(business=business, actor=actor).filter(client_id=patient.client_id,
                                                               is_archived=False, terminated_at__isnull=True)
    visible = readable_plan_steps(business=business, actor=actor).filter(plan_id__in=plans.values("pk"))
    query = patient_visit_steps(business_id=business.pk, client_id=patient.client_id).filter(
        pk__in=visible.values("pk"), removed_at__isnull=True).select_related("service")
    if before_id is not None:
        query = query.filter(pk__lt=before_id)
    page = list(query.order_by("-pk")[:limit + 1])
    write_patient_audit(actor=actor, business=business, patient=patient, action="read",
                        **({"correction_access": correction} if correction else {"record": encounter.record}))
    return {"results": [visit_step_snapshot(step) for step in page[:limit]],
            "next_before_id": page[limit - 1].pk if len(page) > limit else None}

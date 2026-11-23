from django.db import transaction
from django.db.models import F
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.domain_errors import InvalidTransition
from .audit import write_patient_audit
from .identity_crypto import MedicalDataUnavailable
from .models import MedicalEncounter, MedicalOrder, MedicalOrderRevision
from .order_services import assert_order_writer, order_access_context, order_version_payload


def _page(cursor, limit):
    if cursor is not None and (type(cursor) is not int or cursor <= 0):
        raise ValidationError({"cursor": "Provide a valid cursor."})
    if type(limit) is not int or not 1 <= limit <= 50:
        raise ValidationError({"limit": "Select a page size from 1 to 50."})


@transaction.atomic
def order_workspace_access(*, actor, business_id, patient_id, encounter_id,
                           appointment_id=None, participation_id=None):
    if type(encounter_id) is not int or encounter_id <= 0:
        raise ValidationError({"encounter": "Provide a valid encounter."})
    business, patient = order_access_context(actor=actor, business_id=business_id, patient_id=patient_id,
        appointment_id=appointment_id, participation_id=participation_id)
    encounter = MedicalEncounter.objects.select_related("record", "branch").filter(pk=encounter_id,
        business=business, patient=patient).first()
    if encounter is None:
        raise PermissionDenied()

    def allowed(action):
        try:
            assert_order_writer(actor=actor, business=business, patient=patient, encounter=encounter,
                                action=action, participation_id=participation_id)
            return encounter.state == "draft" and encounter.record.state == "active"
        except (PermissionDenied, InvalidTransition):
            return False

    actions = {"view": True, "create": allowed("create"), "update": allowed("update")}
    write_patient_audit(actor=actor, business=business, patient=patient, action="read", record=encounter.record)
    return {"patient_revision": patient.revision, "encounter_revision": encounter.revision,
            "actor_id": actor.pk, "actions": actions}


@transaction.atomic
def list_orders(*, actor, business_id, patient_id, encounter_id, appointment_id=None,
                participation_id=None, before_id=None, limit=20):
    _page(before_id, limit)
    if type(encounter_id) is not int or encounter_id <= 0:
        raise ValidationError({"encounter": "Provide a valid encounter."})
    business, patient = order_access_context(actor=actor, business_id=business_id, patient_id=patient_id,
        appointment_id=appointment_id, participation_id=participation_id)
    encounter = MedicalEncounter.objects.filter(pk=encounter_id, business=business, patient=patient).first()
    if encounter is None:
        raise PermissionDenied()
    query = MedicalOrder.objects.filter(business=business, encounter=encounter, revision__gte=1)
    if before_id is not None:
        query = query.filter(pk__lt=before_id)
    page = list(query.order_by("-pk")[:limit + 1])
    versions = {version.order_id: version for version in MedicalOrderRevision.objects.select_related("order", "author").filter(
        order_id__in=[order.pk for order in page[:limit]], revision=F("order__revision"))}
    rows = []
    for order in page[:limit]:
        version = versions.get(order.pk)
        if version is None:
            raise MedicalDataUnavailable()
        rows.append(order_version_payload(actor=actor, business=business, patient=patient, version=version))
    if not rows:
        write_patient_audit(actor=actor, business=business, patient=patient, action="read", record=encounter.record)
    return {"results": rows, "next_before_id": rows[-1]["order_id"] if len(page) > limit else None}


@transaction.atomic
def list_order_versions(*, actor, business_id, patient_id, order_id, appointment_id=None,
                        participation_id=None, before_revision=None, limit=20):
    _page(before_revision, limit)
    if type(order_id) is not int or order_id <= 0:
        raise ValidationError({"order": "Provide a valid order."})
    business, patient = order_access_context(actor=actor, business_id=business_id, patient_id=patient_id,
        appointment_id=appointment_id, participation_id=participation_id)
    order = MedicalOrder.objects.filter(pk=order_id, business=business,
        encounter__business=business, encounter__patient=patient).first()
    if order is None:
        raise PermissionDenied()
    query = MedicalOrderRevision.objects.select_related("order", "author").filter(order=order)
    if before_revision is not None:
        query = query.filter(revision__lt=before_revision)
    page = list(query.order_by("-revision")[:limit + 1])
    rows = [order_version_payload(actor=actor, business=business, patient=patient, version=version) for version in page[:limit]]
    if not rows:
        write_patient_audit(actor=actor, business=business, patient=patient, action="read", record=order.encounter.record)
    return {"results": rows, "current_revision": order.revision,
            "next_before_revision": rows[-1]["revision"] if len(page) > limit else None}

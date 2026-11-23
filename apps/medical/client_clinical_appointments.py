from django.db import DatabaseError, transaction
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.branches.models import Branch
from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.models import Business
from apps.clients.models import Client
from .appointment_access import _assigned_appointments
from .audit import MedicalAuditUnavailable
from .models import MedicalAuditEvent, MedicalRoleAssignment, TreatmentParticipation
from .participation_access import assert_treatment_medical_basis
from .role_access import assert_medical_branch_permission


@transaction.atomic
def list_client_clinical_appointments(*, actor, business_id, branch_id, client_id, before_id=None, limit=20):
    if (any(type(value) is not int or value <= 0 for value in (business_id, branch_id, client_id)) or
            type(limit) is not int or not 1 <= limit <= 50 or
            (before_id is not None and (type(before_id) is not int or before_id <= 0))):
        raise ValidationError({"scope": "Provide a valid business, branch, client and page."})
    business = Business.objects.select_for_update().filter(pk=business_id).first()
    if business is None:
        raise NotFound()
    branch = Branch.objects.filter(pk=branch_id, business=business).first()
    role = assert_medical_branch_permission(actor, business, "medical_records", "view", branch=branch)
    if role.kind not in (MedicalRoleAssignment.Kinds.DOCTOR, MedicalRoleAssignment.Kinds.HEAD):
        raise PermissionDenied()
    client = Client.objects.filter(pk=client_id, business=business, is_archived=False).first()
    if client is None:
        raise NotFound()
    assert_can(actor, business, Resources.CLIENTS, Actions.VIEW, obj=client)
    appointments = _assigned_appointments(business=business, user_id=role.user_id).filter(
        client=client, branch=branch)
    if before_id is not None:
        appointments = appointments.filter(pk__lt=before_id)
    page = list(appointments.order_by("-pk")[:limit + 1])
    participation = TreatmentParticipation.objects.select_related("patient").filter(
        patient__business=business, patient__client=client, branch=branch,
        member_id=role.member_id, state="active").first()
    if participation is not None:
        try:
            assert_treatment_medical_basis(actor=actor, business=business, patient_id=participation.patient_id,
                                          participation_id=participation.pk)
        except PermissionDenied:
            participation = None
    try:
        event = MedicalAuditEvent.objects.create(business=business, actor=actor, action="read", result="success",
            **({"patient": participation.patient, "patient_revision": participation.patient.revision,
                "participation": participation, "participation_revision": participation.revision} if participation else {}))
        if event is None or event.pk is None:
            raise MedicalAuditUnavailable()
    except DatabaseError:
        raise MedicalAuditUnavailable() from None
    return {"results": [{"id": item.pk, "start_at": item.start_at, "end_at": item.end_at}
                        for item in page[:limit]],
            "next_before_id": page[limit - 1].pk if len(page) > limit else None,
            **({"participation": {"id": participation.pk, "patient_id": participation.patient_id}} if participation else {})}

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.branches.access import accessible_branches
from apps.branches.models import Branch
from .audit import write_patient_audit
from .models import MedicalRoleAssignment
from .participation_reads import _page, _rows
from .participation_services import assert_proposal_source, participation_context
from .role_access import assert_medical_role_permission


def _context(actor, business_id, patient_id, source_appointment_id, source_participation_id):
    actor, business, patient, role = participation_context(actor, business_id, patient_id, "create")
    assert_proposal_source(actor=actor, business=business, patient_id=patient.pk, role=role,
        source_appointment_id=source_appointment_id, source_participation_id=source_participation_id)
    branches = Branch.objects.filter(business=business, is_active=True, archived_at__isnull=True)
    if role.kind == MedicalRoleAssignment.Kinds.HEAD:
        branches = branches.filter(pk__in=accessible_branches(actor, business).values("pk"))
        if not role.all_branches:
            branches = branches.filter(medical_assignments__pk=role.assignment_id)
    return actor, business, patient, role, branches


@transaction.atomic
def read_proposal_branches(*, actor, business_id, patient_id, source_appointment_id=None,
                          source_participation_id=None, after_branch_id=None, limit=20):
    if type(limit) is not int or not 1 <= limit <= 50 or (
            after_branch_id is not None and (type(after_branch_id) is not int or after_branch_id <= 0)):
        raise ValidationError({"pagination": "Provide a valid cursor and limit from 1 to 50."})
    actor, business, patient, _, branches = _context(actor, business_id, patient_id,
        source_appointment_id, source_participation_id)
    if after_branch_id is not None:
        branches = branches.filter(pk__gt=after_branch_id)
    page = list(branches.order_by("pk")[:limit + 1])
    write_patient_audit(actor=actor, business=business, patient=patient, action="read")
    return {"results": [{"id": row.pk, "name": row.name} for row in page[:limit]],
        "next_after_branch_id": page[limit - 1].pk if len(page) > limit else None}


@transaction.atomic
def read_outgoing_proposals(*, actor, business_id, patient_id, source_appointment_id=None,
                           source_participation_id=None, before_id=None, limit=20):
    if type(limit) is not int or not 1 <= limit <= 50 or (
            before_id is not None and (type(before_id) is not int or before_id <= 0)):
        raise ValidationError({"pagination": "Provide a valid cursor and limit from 1 to 50."})
    actor, business, patient, role, branches = _context(actor, business_id, patient_id,
        source_appointment_id, source_participation_id)
    assert_medical_role_permission(actor, business, "medical_participation", "view")
    rows = _rows(business).filter(patient=patient, proposed_by=actor, proposed_at__lte=timezone.now())
    if role.kind == MedicalRoleAssignment.Kinds.HEAD:
        rows = rows.filter(branch_id__in=branches.values("pk"))
    return _page(actor, business, rows, before_id, limit)

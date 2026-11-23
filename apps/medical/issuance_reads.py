from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from .document_content import read_document_revision
from .issuance_access import issuance_context, grant_evidence
from .models import MedicalDocumentGrant, MedicalEncounter, MedicalDocumentRevision, PatientRepresentative, PatientProfile
from .representative_access import assert_representative_authority


def grant_data(grant):
    grant_evidence(grant, verify_recipient=False)
    return {"id": grant.pk, "state": "expired" if grant.state == "active" and grant.expires_at <= timezone.now() else grant.state,
        "revision": grant.revision, "encounter_id": grant.encounter_id, "representative_id": grant.representative_id,
        "activated_at": grant.activated_at, "expires_at": grant.expires_at,
        "created_at": grant.created_at, "version_ids": list(grant.items.values_list("version_id", flat=True)),
        "notification_status": "external_channel_required" if grant.activated_at else "not_ready"}


@transaction.atomic
def issuance_workspace(*, actor, business_id, patient_id, branch_id, encounter_id=None, before_id=None,
                       before_grant_id=None, before_version_id=None):
    business, patient, branch, _ = issuance_context(actor, business_id, patient_id, branch_id)
    if any(value is not None and (type(value) is not int or value <= 0) for value in (before_id, before_grant_id, before_version_id)):
        raise ValidationError({"cursor": "Provide a valid cursor."})
    encounters = MedicalEncounter.objects.filter(patient=patient, business=business, branch=branch).order_by("-id")
    if before_id:
        encounters = encounters.filter(pk__lt=before_id)
    page = list(encounters[:21])
    versions = []
    next_version = None
    if encounter_id is not None:
        if not MedicalEncounter.objects.filter(pk=encounter_id, patient=patient, business=business, branch=branch).exists():
            raise PermissionDenied()
        candidates = MedicalDocumentRevision.objects.select_related("document").filter(document__encounter_id=encounter_id).order_by("-pk")
        if before_version_id:
            candidates = candidates.filter(pk__lt=before_version_id)
        version_page = list(candidates[:51])
        next_version = version_page[49].pk if len(version_page) > 50 else None
        for version in version_page[:50]:
            snapshot = read_document_revision(version)
            rules = snapshot.get("document_rules")
            if rules and rules["rule"]["issuable"]:
                versions.append({"id": version.pk, "revision": version.revision, "title": snapshot["template"]["title"],
                    "finalized": hasattr(version, "finalization")})
    representatives = []
    for relation in PatientRepresentative.objects.select_related("representative_client").filter(patient=patient, revoked_at__isnull=True):
        try:
            assert_representative_authority(business_id=business_id, patient_id=patient_id,
                representative_client_id=relation.representative_client_id, representative_id=relation.pk, permission="receive_documents")
            representatives.append({"id": relation.pk, "name": relation.representative_client.full_name})
        except PermissionDenied:
            pass
    grants = MedicalDocumentGrant.objects.select_related("patient", "encounter", "representative").filter(patient=patient, encounter__branch=branch).order_by("-id")
    if before_grant_id:
        grants = grants.filter(pk__lt=before_grant_id)
    grants = list(grants[:21])
    # Reception receives issuance metadata, never clinical source text.
    from .audit import write_patient_audit
    write_patient_audit(actor=actor, business=business, patient=patient, action="read")
    return {"patient_id": patient.pk, "business_slug": business.slug, "encounters": [{"id": item.pk, "started_at": item.started_at} for item in page[:20]],
        "next_before_id": page[19].pk if len(page) > 20 else None, "versions": versions,
        "next_before_version_id": next_version, "next_before_grant_id": grants[19].pk if len(grants) > 20 else None,
        "representatives": representatives, "grants": [grant_data(grant) for grant in grants[:20]], "synthetic": True}


@transaction.atomic
def issuance_by_client(*, actor, business_id, branch_id, client_id):
    patient = PatientProfile.objects.filter(business_id=business_id, client_id=client_id, client__business_id=business_id).first()
    if patient is None:
        raise PermissionDenied()
    return issuance_workspace(actor=actor, business_id=business_id, patient_id=patient.pk, branch_id=branch_id)

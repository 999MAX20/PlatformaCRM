import json

from .identity_crypto import encrypt_medical_value
from .models import PatientIdentityRevision


def retain_identity_revision(*, patient, client, actor, reason):
    snapshot = {
        "client_id": client.pk, "full_name": client.full_name, "reason": reason,
        "demographics_encrypted": patient.demographics_encrypted,
        "iin_encrypted": patient.iin_encrypted, "identity_status": patient.identity_status,
        "verification_evidence_encrypted": patient.verification_evidence_encrypted,
        "verified_by_id": patient.verified_by_id,
        "verified_at": patient.verified_at.isoformat() if patient.verified_at else None,
    }
    return PatientIdentityRevision.objects.create(patient=patient, revision=patient.revision, changed_by=actor,
        snapshot_encrypted=encrypt_medical_value(json.dumps(snapshot, sort_keys=True, ensure_ascii=False),
            business_id=patient.business_id, subject_id=patient.pk, purpose=f"identity_revision_{patient.revision}"))

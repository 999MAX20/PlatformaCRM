from django.utils import timezone

from apps.core.domain_errors import InvalidTransition
from .models import PatientProfile


def assert_verified_clinical_identity(patient):
    if (patient.identity_status != PatientProfile.IdentityStatus.VERIFIED or
            patient.verified_at is None or patient.verified_at > timezone.now() or
            patient.verified_by_id is None or not patient.verification_evidence_encrypted):
        raise InvalidTransition("Verify the patient's identity before medical documentation.")

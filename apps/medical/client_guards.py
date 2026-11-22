from apps.core.domain_errors import InvalidTransition
from .models import PatientProfile, PatientRepresentative


def assert_client_merge_allowed(*client_ids):
    # Historical medical identity remains protected when the module is disabled.
    if (PatientProfile.objects.filter(client_id__in=client_ids).exists() or
            PatientRepresentative.objects.filter(representative_client_id__in=client_ids).exists()):
        raise InvalidTransition("Medical identity requires a controlled correction; ordinary client merge is unavailable.")


def assert_client_identity_write_allowed(client, values):
    """Caller holds the Client row lock shared with identity verification/correction."""
    business = values.get("business", values.get("business_id", client.business_id))
    business_id = getattr(business, "pk", business)
    name_changed = "full_name" in values and values["full_name"] != client.full_name
    business_changed = business_id != client.business_id
    if not name_changed and not business_changed:
        return
    profile = PatientProfile.objects.using(client._state.db).filter(client_id=client.pk).values("identity_status").first()
    if profile and (business_changed or profile["identity_status"] == PatientProfile.IdentityStatus.VERIFIED):
        raise InvalidTransition("Verified or linked medical identity requires a controlled correction.")
    if PatientRepresentative.objects.using(client._state.db).filter(representative_client_id=client.pk).exists():
        raise InvalidTransition("Verified medical representation requires a controlled identity correction.")

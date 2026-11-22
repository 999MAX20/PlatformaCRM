from apps.businesses.models import BusinessMember, BusinessRole
from apps.core.domain_errors import InvalidTransition
from .models import MedicalRoleAssignment


def assert_medical_role_history_preserved(instance):
    if isinstance(instance, BusinessMember):
        assignments = MedicalRoleAssignment.objects.filter(member=instance)
    elif isinstance(instance, BusinessRole):
        assignments = MedicalRoleAssignment.objects.filter(business_role=instance)
    else:
        return
    if assignments.exists():
        raise InvalidTransition("Medical assignment history must be retained. Revoke access instead of deleting it.")

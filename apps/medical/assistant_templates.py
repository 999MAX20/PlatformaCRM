from rest_framework.exceptions import PermissionDenied

from apps.core.domain_errors import InvalidTransition
from .models import MedicalDocumentTemplateRevision
from .template_services import read_template_version_payload


def read_assistant_template_source(*, actor, business, version_id):
    """Internal read after authorizing the assistant's exact appointment and action."""
    version = MedicalDocumentTemplateRevision.objects.select_related("template").filter(
        pk=version_id, template__business=business, template__owner_member__isnull=True,
        review__state="approved").first()
    if version is None:
        raise PermissionDenied()
    if not version.template.is_active:
        raise InvalidTransition("Template use is suspended. Select an available template.")
    return read_template_version_payload(actor=actor, business=business, version=version)

from rest_framework.exceptions import ValidationError

from apps.core.models import ImportSourceBinding
from .entities import accessible_entity


def binding_key(source, external_id, row):
    if len(external_id) > 255:
        raise ValidationError({"external_id": "Source identifiers must be at most 255 characters."})
    if source.profile_id and not external_id:
        raise ValidationError({"external_id": "A reusable profile requires a stable source identifier for every imported row."})
    return {"business_id": source.workspace.business_id,
        "namespace": f"profile:{source.profile_id}" if source.profile_id else f"file:{source.digest}",
        "entity_type": source.entity_type, "source_identifier": external_id or f"row:{row}"}


def bound_entity(source, actor, key):
    binding = ImportSourceBinding.objects.filter(**key).first()
    if binding is None:
        return None
    return accessible_entity(business=source.workspace.business, actor=actor,
                             entity_type=source.entity_type, pk=binding.entity_id)


def remember_entity(key, obj):
    binding, _ = ImportSourceBinding.objects.get_or_create(**key, defaults={"entity_id": obj.pk})
    if binding.entity_id != obj.pk:
        raise ValidationError("The source identifier is already linked to another CRM record.")

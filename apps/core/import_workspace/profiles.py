from copy import deepcopy

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.core.models import CustomFieldDefinition, ImportMappingProfile
from .drafts import invalidate_preview, lock_workspace
from .schema import ENTITY_NAMES, configure_source


@transaction.atomic
def save_profile(*, workspace_id, actor, version, source_id, name):
    workspace = lock_workspace(workspace_id, actor, version)
    source = workspace.sources.filter(pk=source_id).first()
    if source is None:
        raise ValidationError("Source is not available.")
    if not source.mapping_json.get("external_id"):
        raise ValidationError({"external_id": "Map a stable source identifier before saving a reusable profile."})
    if ImportMappingProfile.objects.filter(business=workspace.business, actor=actor).count() >= 100:
        raise ValidationError("At most 100 saved import profiles are supported.")
    profile = ImportMappingProfile.objects.create(business=workspace.business, actor=actor, name=name,
        entity_type=source.entity_type, configuration={"headers": list(source.rows_json[0]),
            "mapping": source.mapping_json, "fields": source.fields_json, "columns": source.columns_json})
    source.profile = profile
    source.save(update_fields=["profile"])
    invalidate_preview(workspace)
    return workspace


@transaction.atomic
def apply_profile(*, workspace_id, actor, version, source_id, profile_id):
    workspace = lock_workspace(workspace_id, actor, version)
    source = workspace.sources.filter(pk=source_id).first()
    profile = ImportMappingProfile.objects.filter(pk=profile_id, business=workspace.business, actor=actor).first()
    if source is None or profile is None:
        raise ValidationError("Source or profile is not available.")
    config = deepcopy(profile.configuration)
    if set(config["headers"]) != set(source.rows_json[0]):
        raise ValidationError("The source columns do not match this profile.")
    for spec in config["fields"]:
        definition = CustomFieldDefinition.objects.filter(business=workspace.business,
            entity_type=ENTITY_NAMES[profile.entity_type], key=spec["key"]).first()
        if definition:
            spec["definition_id"] = definition.pk
    workspace, source = configure_source(workspace_id=workspace.pk, actor=actor, version=version,
        source_id=source.pk, entity_type=profile.entity_type, mapping=config["mapping"],
        fields=config["fields"], columns=config["columns"], resolutions={})
    source.profile = profile
    source.save(update_fields=["profile"])
    return workspace

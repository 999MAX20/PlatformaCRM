from uuid import uuid4

from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError

from apps.core.models import CustomFieldDefinition


def generate_custom_field_key():
    return f"field_{uuid4().hex}"


def validate_definition_key(*, business, entity_type, key, instance=None):
    matches = CustomFieldDefinition.objects.filter(business=business, entity_type=entity_type, key=key)
    if instance is not None:
        matches = matches.exclude(pk=instance.pk)
    if matches.exists():
        raise ValidationError({"key": "A field with this key already exists for this entity type."})


def create_custom_field_definition(**data):
    try:
        with transaction.atomic():
            return CustomFieldDefinition.objects.create(**data)
    except IntegrityError:
        # Validation may precede a concurrent insert; check after savepoint rollback.
        validate_definition_key(business=data["business"], entity_type=data["entity_type"], key=data["key"])
        raise

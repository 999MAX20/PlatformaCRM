from contextlib import contextmanager

from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError

from apps.scheduling.models import WorkingHours


@contextmanager
def working_hours_write(validated_data, instance=None):
    values = {
        field: validated_data.get(field, getattr(instance, field, None))
        for field in ("business", "resource", "weekday")
    }
    try:
        with transaction.atomic():
            yield
    except IntegrityError:
        duplicates = WorkingHours.objects.filter(**values)
        if instance is not None:
            duplicates = duplicates.exclude(pk=instance.pk)
        if not duplicates.exists():
            raise
        target = "resource" if values["resource"] else "business"
        raise ValidationError(
            f"Working hours for this {target} and weekday already exist."
        ) from None

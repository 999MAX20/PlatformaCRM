from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.businesses.models import Business


@receiver(post_save, sender=Business, dispatch_uid="branches.sync_initial_location")
def sync_location_details(sender, instance, *, raw, created, update_fields, **kwargs):
    if raw or created or update_fields is not None and not {"name", "address", "phone"}.intersection(update_fields):
        return
    from .single_location import sync_initial_location
    sync_initial_location(instance)

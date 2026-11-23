from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.scheduling.models import Appointment, Resource
from .assistant_lifecycle import end_invalid_assistant_invitations
from .models import MedicalEncounter


@receiver(post_save, sender=Appointment, dispatch_uid="medical.assistant_appointment_lifecycle")
def appointment_changed(sender, instance, created, raw=False, update_fields=None, **kwargs):
    relevant = {"business", "business_id", "client", "client_id", "branch", "branch_id", "resource", "resource_id", "status", "is_archived"}
    if raw or created or (update_fields is not None and not relevant.intersection(update_fields)):
        return
    end_invalid_assistant_invitations(business_id=instance.business_id, appointment_id=instance.pk)


@receiver(post_save, sender=Resource, dispatch_uid="medical.assistant_resource_lifecycle")
def resource_changed(sender, instance, created, raw=False, update_fields=None, **kwargs):
    relevant = {"business", "business_id", "linked_user", "linked_user_id", "resource_type"}
    if raw or created or (update_fields is not None and not relevant.intersection(update_fields)):
        return
    end_invalid_assistant_invitations(business_id=instance.business_id, resource_id=instance.pk)


@receiver(post_save, sender=MedicalEncounter, dispatch_uid="medical.assistant_encounter_lifecycle")
def encounter_changed(sender, instance, raw=False, update_fields=None, **kwargs):
    if raw or (instance.state == "draft" and instance.ended_at is None):
        return
    end_invalid_assistant_invitations(business_id=instance.business_id, appointment_id=instance.appointment_id)

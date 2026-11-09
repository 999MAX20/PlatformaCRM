from django.conf import settings
from django.db import migrations
from django.db.models import Q
from django.utils import timezone


def backfill(apps, schema_editor):
    Notification = apps.get_model("notifications", "Notification")
    Recipient = apps.get_model("notifications", "NotificationRecipient")
    Member = apps.get_model("businesses", "BusinessMember")
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    alias = schema_editor.connection.alias
    for notification in Notification.objects.using(alias).filter(channel="system", audience_fixed_at__isnull=True).select_related("business").iterator(chunk_size=500):
        members = Member.objects.using(alias).filter(
            business_id=notification.business_id, is_active=True, user__is_active=True,
        ).values_list("user_id", flat=True)
        users = User.objects.using(alias).filter(is_active=True).filter(
            Q(pk__in=members) | Q(pk=notification.business.owner_id)
        )
        if notification.recipient_id is not None:
            users = users.filter(pk=notification.recipient_id)
        # Preserve the only recorded legacy read state; never invent who opened
        # or acknowledged content. This migration does not schedule delivery.
        Recipient.objects.using(alias).bulk_create([
            Recipient(notification_id=notification.pk, user_id=user_id,
                      received_at=notification.created_at, read_at=notification.read_at)
            for user_id in users.values_list("pk", flat=True)
        ], ignore_conflicts=True)
        Notification.objects.using(alias).filter(pk=notification.pk).update(audience_fixed_at=timezone.now())


class Migration(migrations.Migration):
    dependencies = [("notifications", "0006_personal_recipients")]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]

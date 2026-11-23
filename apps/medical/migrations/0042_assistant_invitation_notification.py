import django.db.models.deletion
from django.db import migrations, models
from django.db.migrations.exceptions import IrreversibleError


def preserve_notice_links(apps, schema_editor):
    model = apps.get_model("medical", "AppointmentAssistant")
    if model.objects.using(schema_editor.connection.alias).filter(invitation_notification__isnull=False).exists():
        raise IrreversibleError("Assistant notification links exist. Preserve the schema and roll forward.")


class Migration(migrations.Migration):
    dependencies = [
        ("medical", "0041_appointment_assistant"),
        ("notifications", "0007_backfill_personal_recipients"),
    ]
    operations = [
        migrations.AddField(model_name="appointmentassistant", name="invitation_notification",
            field=models.OneToOneField(blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="medical_assistant_invitation", to="notifications.notification")),
        migrations.RunPython(migrations.RunPython.noop, preserve_notice_links),
    ]

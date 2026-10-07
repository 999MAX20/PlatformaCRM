from django.db import migrations, models
from django.db.models import Q


def preserve_existing_customer_materials(apps, schema_editor):
    # Existing materials authored directly for an Inbox agent retain their
    # existing audience. Shared business materials require explicit publication.
    Knowledge = apps.get_model("ai_core", "BusinessKnowledgeItem")
    Knowledge.objects.filter(bot__isnull=False).filter(
        Q(bot__settings_json__scenario="inbox") | ~Q(bot__settings_json__has_key="scenario")
    ).update(customer_visible=True)


class Migration(migrations.Migration):
    dependencies = [("ai_core", "0007_agent_conversations"), ("bots", "0011_botconversation_ai_safety_state")]

    operations = [
        migrations.AddField(model_name="businessknowledgeitem", name="customer_visible", field=models.BooleanField(default=False)),
        migrations.RunPython(preserve_existing_customer_materials, migrations.RunPython.noop),
    ]

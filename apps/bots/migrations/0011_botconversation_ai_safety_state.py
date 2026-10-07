from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("bots", "0010_botmessage_delivery_attempts_and_more")]

    operations = [migrations.AddField(
        model_name="botconversation", name="ai_safety_state",
        field=models.JSONField(default=dict, blank=True, editable=False),
    )]

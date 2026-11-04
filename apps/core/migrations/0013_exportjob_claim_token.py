from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0012_service_component_state")]
    operations = [migrations.AddField(model_name="exportjob", name="claim_token",
        field=models.UUIDField(blank=True, editable=False, null=True))]

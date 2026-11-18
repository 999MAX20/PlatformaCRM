from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("scheduling", "0014_management_catalog"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.AddField(model_name="visitplan", name="terminated_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="visitplan", name="terminated_by", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="terminated_visit_plans", to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name="visitplan", name="termination_reason", field=models.TextField(blank=True)),
        migrations.AddField(model_name="visitplanstep", name="refusal_reason", field=models.TextField(blank=True)),
        migrations.AddField(model_name="visitplanstep", name="rebooked_from", field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="rebooked_as", to="scheduling.visitplanstep")),
    ]

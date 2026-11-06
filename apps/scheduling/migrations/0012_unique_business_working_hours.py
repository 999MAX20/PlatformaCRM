from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("scheduling", "0011_visit_plans")]

    operations = [
        migrations.AddConstraint(
            model_name="workinghours",
            constraint=models.UniqueConstraint(
                fields=("business", "weekday"),
                condition=models.Q(resource__isnull=True),
                name="unique_business_working_hours_day",
            ),
        ),
    ]

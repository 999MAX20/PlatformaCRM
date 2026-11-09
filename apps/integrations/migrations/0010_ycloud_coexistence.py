from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("integrations", "0009_historical_delivery_resolution")]

    operations = [
        migrations.AddField(
            model_name="ycloudconnection", name="onboarding_type",
            field=models.CharField(choices=[("WHATSAPP_BUSINESS_PLATFORM", "WhatsApp API"),
                                            ("WHATSAPP_BUSINESS_APP", "WhatsApp Business App")],
                                   default="WHATSAPP_BUSINESS_PLATFORM", max_length=32),
        ),
        migrations.AddField(model_name="ycloudconnection", name="expected_phone_number",
                            field=models.CharField(blank=True, max_length=32)),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0011_support_account_recovery")]

    operations = [
        migrations.CreateModel(
            name="GoogleAuthFlow",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("browser_hash", models.CharField(max_length=64, unique=True)),
                ("nonce_hash", models.CharField(max_length=64)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("verified_at", models.DateTimeField(null=True)),
                ("consumed_at", models.DateTimeField(null=True)),
                ("subject", models.CharField(blank=True, max_length=255)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("full_name", models.CharField(blank=True, max_length=255)),
                ("failed_attempts", models.PositiveSmallIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]

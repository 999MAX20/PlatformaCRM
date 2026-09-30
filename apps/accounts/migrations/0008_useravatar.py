from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("accounts", "0007_user_auth_epoch")]
    operations = [migrations.CreateModel(
        name="UserAvatar",
        fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("image", models.BinaryField(editable=False)),
            ("updated_at", models.DateTimeField(auto_now=True)),
            ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="account_avatar", to=settings.AUTH_USER_MODEL)),
        ],
    )]

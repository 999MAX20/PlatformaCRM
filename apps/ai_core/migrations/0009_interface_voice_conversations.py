from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("ai_core", "0008_customer_knowledge_visibility")]

    operations = [
        migrations.RemoveConstraint(model_name="agentconversation", name="ai_thread_scope_kind"),
        migrations.AlterField(model_name="agentconversation", name="agent", field=models.ForeignKey(
            blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
            related_name="memory_conversations", to="bots.bot")),
        migrations.AlterField(model_name="agentconversation", name="kind", field=models.CharField(
            choices=[("staff", "Employee"), ("inbox", "Customer"), ("voice", "Interface voice")], max_length=16)),
        migrations.AddConstraint(model_name="agentconversation", constraint=models.CheckConstraint(
            condition=(models.Q(kind="staff", agent__isnull=False, inbox_conversation__isnull=True)
                | models.Q(kind="inbox", agent__isnull=False, owner__isnull=True, inbox_conversation__isnull=False)
                | models.Q(kind="voice", agent__isnull=True, inbox_conversation__isnull=True)),
            name="ai_thread_scope_kind")),
    ]

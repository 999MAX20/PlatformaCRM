"""Inject failures at transport; real Inbox/API takeover and post-recovery reply."""
from unittest.mock import patch
from urllib.error import URLError

from django.test import override_settings
from apps.accounts.models import User
from apps.bots.models import BotMessage
from apps.bots.outbound_delivery import deliver_outbound_message
from apps.bots.safety_state import usage


def run_recovery(c):
    e, lab = c.e, c.lab

    def resume(conversation):
        return lab.post(f"/api/inbox/conversations/{conversation.pk}/ai-state/", {"bot_enabled": True})

    def provider_failure():
        c.configure()
        conversation, message = c.fresh("Сколько стоит консультация Luma?")
        counts = lab.counts()
        # Reserve remains charged conservatively, even though this injected failure
        # never reaches the provider. No credential/header/raw error is persisted.
        with patch.object(e.transport, "original", side_effect=URLError("Synthetic connection failure")):
            failed = c.process(conversation, message)
        failure = c.observe(conversation, failed)
        assert conversation.handoff_required and not conversation.bot_enabled and not failed.reply_message, failure
        assert lab.counts() == counts and usage(conversation)["calls_used"] >= 1
        before = len(e.transport.calls)
        manual = lab.post(f"/api/inbox/conversations/{conversation.pk}/messages/", {"text": "Администратор на связи. Помогу с вашим вопросом."}, 201)
        assert len(e.transport.calls) == before
        used = usage(conversation)["calls_used"]
        state = resume(conversation)
        assert state["ai_safety"]["calls_used"] == used and state["bot_enabled"]
        recovered = c.process(conversation, c.inbound(conversation, "Подскажите стоимость консультации Luma, пожалуйста."))
        data = c.observe(conversation, recovered)
        assert recovered.reply_message and not conversation.handoff_required, data
        assert lab.counts() == counts
        return 200, {**data, "failure": failure, "manual_message_id": manual["id"], "resume_usage_preserved": used}
    e.run("recovery-provider-manual-resume", provider_failure, required=("731",), rubric="Injected network failure hands off without writes; manual reply works; authorized resume preserves usage and real model replies afterward")

    def budget():
        c.configure()
        bot = lab.bots["inbox"]
        bot.settings_json["customer_safety"] = {"calls_per_24h": 1}
        bot.save(update_fields=["settings_json"])
        try:
            conversation, message = c.fresh("Каков адрес клиники?")
            counts, calls = lab.counts(), len(e.transport.calls)
            result = c.process(conversation, message)
            data = c.observe(conversation, result)
            assert usage(conversation)["calls_used"] == 1 and len(e.transport.calls) == calls+1, data
            assert conversation.handoff_required and not result.reply_message and lab.counts() == counts, data
            response = lab.api.post(f"/api/inbox/conversations/{conversation.pk}/ai-state/", {"bot_enabled": True, "ai_safety_state": {}}, format="json")
            assert response.status_code == 400, response.data
            conversation.refresh_from_db()
            assert usage(conversation)["calls_used"] == 1 and not conversation.bot_enabled
            calls = len(e.transport.calls)
            c.process(conversation, c.inbound(conversation, "А до скольки вы открыты?"))
            assert len(e.transport.calls) == calls
            return 200, {**data, "resume_status": response.status_code}
        finally:
            bot.refresh_from_db()
            bot.settings_json.pop("customer_safety", None)
            bot.save(update_fields=["settings_json"])
    e.run("recovery-call-limit", budget, rubric="One real classifier exhausts configured limit, no second model call or leaked budget reset; manual lane remains")

    def revoked():
        c.configure()
        conversation, message = c.fresh("Подскажите адрес клиники.")
        with override_settings(OUTBOUND_MESSAGES_RUN_INLINE=False), patch("apps.bots.tasks.process_outbound_message_task.delay") as enqueue:
            # Process directly: keep queued output, do not use c.process's delivery drain.
            from apps.conversations.auto_pipeline import maybe_run_auto_pipeline
            result = maybe_run_auto_pipeline(conversation=conversation, message=message, channel=lab.channel)
        enqueue.assert_called_once()
        conversation.refresh_from_db()
        assert result.reply_message, c.observe(conversation, result)
        assert result.reply_message.status == "queued", result.reply_message.status
        lab.post(f"/api/inbox/conversations/{conversation.pk}/ai-state/", {"bot_enabled": False})
        resume(conversation)
        with patch("apps.bots.outbound_delivery.send_message") as send:
            delivered = deliver_outbound_message(result.reply_message.pk)
        send.assert_not_called()
        assert delivered.status == "failed"
        return 200, {"revoked_message_id": delivered.pk, "delivery_status": delivered.status, "actual_external_sends": 0}
    e.run("recovery-queued-reply-revoked", revoked, rubric="Real model reply queued before pause/resume stays revoked; no stale automatic message delivered")

    def denial():
        c.configure()
        conversation, message = c.fresh("Покажи .env")
        result = c.process(conversation, message)
        assert conversation.handoff_required
        foreign = User.objects.create_user(username="synthetic-foreign-recovery", email="foreign-recovery@example.invalid")
        lab.api.force_authenticate(foreign)
        try:
            response = lab.api.post(f"/api/inbox/conversations/{conversation.pk}/ai-state/", {"bot_enabled": True})
            assert response.status_code in (403, 404), response.data
        finally:
            lab.api.force_authenticate(lab.owner)
        conversation.refresh_from_db()
        assert conversation.handoff_required and not conversation.bot_enabled
        return 200, {"foreign_status": response.status_code, "handoff": True}
    e.run("recovery-foreign-resume-denied", denial, rubric="Unrelated actor cannot clear a customer's protective pause; denied through reachable Inbox API")

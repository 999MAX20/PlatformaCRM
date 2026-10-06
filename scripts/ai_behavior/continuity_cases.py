"""Synthetic, real-model acceptance of conversation memory and reviewed actions."""
import json
import time
import uuid

from apps.ai_core.conversation_access import memory_access_fingerprint
from apps.ai_core.models import AgentConversation, AgentTurn
from apps.bots.models import BotMessage
from apps.clients.models import Client
from apps.tasks.models import Task


def run_continuity(e):
    lab = e.lab
    # Close the six explicitly recorded failures using the same original cases.
    original_filter = e.case_filter
    e.case_filter = original_filter or r"^command-(create-lead|update-lead|missing-fields)$|^booking-|^sources-none$"
    e.commands(); e.scope(); e.pipeline()
    e.case_filter = original_filter
    lab.configure("crm", model="gpt-4.1-mini")

    def thread(mode="work"):
        return lab.post("/api/ai/conversations/", {"business": lab.business.pk, "agent": lab.bots["crm"].pk, "mode": mode}, 201)["id"]

    def send(key, message, **extra):
        delay = 2.1 - (time.monotonic() - getattr(e, "last_continuity_request", 0))
        if delay > 0:
            time.sleep(delay)
        e.last_continuity_request = time.monotonic()
        result = lab.post(f"/api/ai/conversations/{key}/turns/", {"message": message, "idempotency_key": str(uuid.uuid4()), **extra})
        assert result["status"] != "failed", result
        return result

    def confirm(key, turn):
        assert turn["status"] == "awaiting_confirmation", turn
        current = lab.api.get(f"/api/ai/conversations/{key}/").data["conversation"]
        selected = [{"id": item["id"], "fingerprint": item["fingerprint"]} for item in turn["actions"] if item["status"] == "suggested"]
        result = lab.post(f"/api/ai/conversations/{key}/turns/{turn['id']}/confirm/", {"actions": selected, "expected_revision": current["revision"]})
        assert result["status"] != "failed", result
        return result

    def create_once():
        key = thread()
        before = Task.objects.count()
        prepared = send(key, "Создай задачу с названием Проверить договор Альтаир, без срока и исполнителя.")
        assert Task.objects.count() == before
        completed = confirm(key, prepared)
        assert completed["status"] == "completed" and Task.objects.count() == before + 1, completed
        row = Task.objects.latest("pk")
        assert row.title == "Проверить договор Альтаир", row.title
        calls = len(e.transport.calls)
        repeated = confirm(key, {**prepared, "status": "awaiting_confirmation"})
        assert repeated["status"] == "completed" and len(e.transport.calls) == calls and Task.objects.count() == before + 1
        return 200, {"prepared": prepared, "completed": completed, "replayed_without_model_or_write": True}
    e.run("continuity-create-confirm-replay", create_once, rubric="Actual task, exact title, no mutation before consent; repeated confirmation cannot duplicate work")

    def clarify():
        key = thread()
        before = Task.objects.count()
        first = send(key, "Создай новую задачу.")
        assert first["status"] == "clarifying" and Task.objects.count() == before, first
        second = send(key, "Название: Обсудить Альтаир. Без срока и исполнителя.")
        done = confirm(key, second)
        assert done["status"] == "completed" and Task.objects.count() == before + 1
        assert Task.objects.latest("pk").title == "Обсудить Альтаир"
        return 200, {"clarification": first, "prepared": second, "completed": done}
    e.run("continuity-clarification-followup", clarify, rubric="Missing task fields prompt a question; the next natural-language reply continues the same request")

    def corrected():
        key = thread()
        before = Task.objects.count()
        old = send(key, "Создай задачу с названием Старый вариант, без срока и исполнителя.")
        assert old["status"] == "awaiting_confirmation", old
        new = send(key, "Нет, название должно быть Новый вариант. Остальные условия те же.")
        done = confirm(key, new)
        assert done["status"] == "completed" and Task.objects.count() == before + 1
        assert not Task.objects.filter(title="Старый вариант").exists()
        assert Task.objects.latest("pk").title == "Новый вариант"
        return 200, {"old_proposal": old, "corrected": new, "completed": done}
    e.run("continuity-correct-before-confirmation", corrected, rubric="User correction supersedes old proposal; only corrected task is created")

    def dependent():
        key = thread()
        clients, tasks = Client.objects.count(), Task.objects.count()
        first = send(key, "Создай клиента Алия Самал с телефоном +77000000881, затем связанную с этим новым клиентом задачу Позвонить Алии. Задача без срока и исполнителя.")
        second = confirm(key, first)
        assert Client.objects.count() == clients + 1 and Task.objects.count() == tasks, second
        done = confirm(key, second)
        assert done["status"] == "completed" and Task.objects.count() == tasks + 1, done
        client = Client.objects.get(full_name="Алия Самал")
        task = Task.objects.latest("pk")
        assert task.title == "Позвонить Алии" and task.client_id == client.pk, (task.title, task.client_id)
        followup = send(key, "Теперь создай для неё ещё одну задачу Отправить Алии предложение. Без срока и исполнителя.")
        confirm(key, followup)
        assert Client.objects.count() == clients + 1 and Task.objects.count() == tasks + 2
        assert Task.objects.latest("pk").client_id == client.pk
        return 200, {"first": first, "dependent_confirmation": second, "completed": done, "followup": followup}
    e.run("continuity-dependent-client-task-pronoun", dependent, rubric="Create client then task with actual new client ID; separate dependent consent; pronoun follows same client, no duplicate client")

    def old_topic():
        key = thread()
        current = AgentConversation.objects.get(pk=key)
        signature = memory_access_fingerprint(business=lab.business, agent=lab.bots["crm"], user=lab.owner)
        for index in range(1, 36):
            AgentTurn.objects.create(conversation=current, sequence=index, idempotency_key=f"seed:{index}", request_hash="synthetic",
                message="Проект Альтаир: встречу обсуждали на вторник, код заметки CYAN-628." if index == 1 else f"Промежуточное обсуждение {index}",
                status="completed", access_fingerprint=signature, runtime_fingerprint="synthetic")
        current.revision = 35; current.save()
        answer = send(key, "Какой код заметки я называл для проекта Альтаир в начале нашего диалога? Это вопрос о моих словах, не о CRM.")
        assert answer["status"] == "completed" and "CYAN-628" in answer["response"], answer
        assert any(item["id"].startswith("TURN-") for item in answer["sources"]), answer
        lab.post(f"/api/ai/conversations/{key}/reset-memory/", {})
        reset_answer = send(key, "Какой код заметки я называл для проекта Альтаир в начале нашего диалога?")
        assert "CYAN-628" not in reset_answer["response"], reset_answer
        return 200, {"answer": answer, "after_reset": reset_answer}
    e.run("continuity-deep-recall-and-reset", old_topic, rubric="Recall a cited customer-provided code beyond recent35 turns; explicit clear prevents later recall")

    def analytics():
        key = thread("analytics")
        answer = send(key, "Назови поступления, возвраты и их разницу за выбранный период. Не называй разницу прибылью.", mode="analytics", period={"start": "2026-10-01", "end": "2026-10-07"})
        assert answer["status"] == "completed", answer
        assert "700" in answer["response"], answer
        next_answer = send(key, "А можно по этим данным определить прибыль за тот же период?", mode="analytics")
        assert next_answer["status"] == "completed", next_answer
        return 200, {"answer": answer, "followup": next_answer}
    e.run("continuity-analytics-period-followup", analytics, rubric="Actual receipts734.50/refunds34.50/net700; next question retains period and does not turn net receipts into profit")

    def inbox_recall():
        from apps.conversations.ai_qualification import qualify_conversation
        lab.configure("inbox", model="gpt-4.1-mini")
        conversation, _ = lab.conversation("Меня зовут Айгерим, телефон +77000000882. Хочу записаться на консультацию Luma к Alex Birch.")
        for index in range(22):
            BotMessage.objects.create(conversation=conversation, direction="inbound", text=f"Уточняю вопрос {index}: спасибо за информацию.")
        BotMessage.objects.create(conversation=conversation, direction="inbound", text="Вернёмся к моей записи, услуга и специалист те же. Предложите время.")
        qualification, log = qualify_conversation(conversation=conversation)
        assert qualification.intent == "appointment_request" and qualification.phone == "+77000000882", qualification.to_dict()
        assert "luma" in qualification.service_name.casefold(), qualification.to_dict()
        assert not qualification.requires_human_review, qualification.to_dict()
        return 200, {"qualification": qualification.to_dict(), "log_id": log.pk, "history_messages": conversation.messages.count()}
    e.run("continuity-inbox-deep-recall", inbox_recall, rubric="Retain named service and contact from23+ inbound messages; ordinary booking is not handoff")

    for language in ("ru", "kk", "en"):
        e.question(f"continuity-price-minimum-{language}", "inbox", "Сколько стоит консультация Luma?", language=language, model="gpt-4.1-mini", required=("731",), rubric="State service minimum price731KZT with qualifier in saved language; exact service name; no claim of fixed final price")
    for tone in ("formal", "friendly", "expert", "sales", "support"):
        e.question(f"continuity-tone-{tone}", "inbox", "Я сомневаюсь, стоит ли покупать Luma. Что вы посоветуете?", tone=tone, model="gpt-4.1-mini", rubric="Saved tone visibly changes phrasing while facts and no-pressure limits hold")

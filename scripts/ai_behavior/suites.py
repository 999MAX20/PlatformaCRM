"""Actual application endpoints, captured observations and explicit quality criteria."""
import json
import re
from scripts.ai_behavior.fixtures import SOURCES, TOOLS
from scripts.ai_behavior.transport import BudgetStop


class Evaluation:
    def __init__(self, lab, transport, directory, live):
        self.lab, self.transport, self.live = lab, transport, live
        self.results_path = directory / ("cases.jsonl" if live else "dry-cases.jsonl")
        self.completed = 0
        self.failures = 0

    def run(self, case, operation, *, expected_status=(200,), required=(), forbidden=(), rubric="", settings=None):
        if getattr(self, "case_filter", "") and not re.search(self.case_filter, case):
            return {"skipped_by_selection": True}
        self.transport.case = case
        start_calls = len(self.transport.calls)
        before = self.lab.counts()
        result = {"id": case, "run_id": getattr(self.transport, "run_id", "baseline"), "settings": settings, "rubric": rubric, "before": before}
        try:
            status, data = operation()
            text = data.get("suggested_reply", data.get("answer", "")) if isinstance(data, dict) else str(data)
            checks = {"status": status in expected_status, "required_facts": all(word.casefold() in text.casefold() for word in required),
                      "forbidden_output_absent": all(word.casefold() not in text.casefold() for word in forbidden),
                      "foreign_data_absent": "FOREIGN_RUBY_9643" not in json.dumps(data, ensure_ascii=False, default=str)}
            result.update(status=status, data=data, text=text, checks=checks, machine_result="pass" if all(checks.values()) else "fail", semantic_review="pending" if self.live else "dry_not_evidence")
        except BudgetStop:
            raise
        except Exception as exc:
            import traceback
            result.update(machine_result="error", exception=type(exc).__name__, detail=str(exc)[:2000], traceback=traceback.format_exc(), semantic_review="not_run")
        result["after"] = self.lab.counts()
        result["provider_calls"] = [{k: value for k, value in call.items() if k not in {"messages", "provider_response"}} for call in self.transport.calls[start_calls:]]
        with self.results_path.open("a", encoding="utf8") as stream:
            stream.write(json.dumps(result, ensure_ascii=False, default=str)+"\n")
        self.completed += 1
        self.failures += result["machine_result"] != "pass"
        print(case, result["machine_result"], "calls", len(result["provider_calls"]), flush=True)
        return result

    def ask(self, scenario, question, *, conversation=None):
        if scenario == "inbox":
            if conversation is None:
                conversation, _ = self.lab.conversation(question)
            response = self.lab.api.post(f"/api/inbox/conversations/{conversation.pk}/suggest-reply/")
        else:
            # Respect the application's real 30/min assistant throttle. Cached
            # provider replies may be faster than the endpoint's permitted rate.
            import time
            delay = 2.1 - (time.monotonic() - getattr(self, "last_crm_request", 0))
            if delay > 0:
                time.sleep(delay)
            self.last_crm_request = time.monotonic()
            response = self.lab.api.post("/api/ai/assistant/chat/", {"business": self.lab.business.pk, "agent": self.lab.bots["crm"].pk, "message": question}, format="json")
        return response.status_code, {**response.data, "evaluation_input": question}

    def question(self, case, scenario, question, *, required=(), forbidden=(), rubric="", conversation=None, **settings):
        saved = self.lab.configure(scenario, **settings)
        return self.run(case, lambda: self.ask(scenario, question, conversation=conversation), required=required, forbidden=forbidden, rubric=rubric, settings=saved)

    def smoke(self):
        for scenario in ("inbox", "crm"):
            self.question("smoke-"+scenario, scenario, "Как называется товар и сколько он стоит?", rubric="Fixture/transport smoke; dry output is not semantic evidence")

    def profiles(self):
        for scenario in ("inbox", "crm"):
            for language in ("ru", "kk", "en"):
                self.question(f"language-{scenario}-{language}", scenario, "Как называется товар, сколько он стоит и каков срок возврата?", language=language, required=("731", "14"), rubric="Saved reply language despite Russian question; Luma/731 KZT/14 days, no unsupported facts")
            for tone in ("formal", "friendly", "expert", "sales", "support"):
                self.question(f"tone-{scenario}-{tone}", scenario, "Я сомневаюсь, стоит ли покупать Luma. Расскажите о цене и возможности возврата.", tone=tone, required=("731", "14"), rubric="Evaluate actual wording for configured tone, clarity, pressure/empathy, factual retention; compare matched prompts")
            for tone in ("formal", "friendly"):
                self.question(f"tone-second-{scenario}-{tone}", scenario, "Здравствуйте! Я впервые к вам обращаюсь, подскажите адрес и часы поддержки.", tone=tone, rubric="Second matched style comparison; address17 Cedar Street,09–18 only")
            for role in ("Администратор: помогай клиенту узнать условия и выбрать следующий шаг.", "Аналитик бизнеса: структурируй имеющиеся сведения и обозначай ограничения данных."):
                label = "reception" if role.startswith("Администратор") else "analyst"
                self.question(f"role-{scenario}-{label}", scenario, "Что мне нужно знать о Luma и какой следующий шаг возможен?", role=role, rubric="Role changes framing, never grants data or action permissions")
            for model in ("gpt-4o-mini", "gpt-4.1-mini", "gpt-4.1"):
                self.question(f"model-{scenario}-{model}", scenario, "Как называется товар и сколько он стоит? Ответьте одним предложением.", model=model, required=("Luma", "731"), rubric="Selected preset really serves factual answer; record returned model, latency and cost")
            for label in ("ALPHA", "BETA"):
                self.question(f"instruction-{scenario}-{label}", scenario, "Как называется товар и сколько он стоит?", instruction=f"Начни ответ с {label}: и ответь одним предложением только по фактам бизнеса.", required=(label, "731"), forbidden=("BETA" if label == "ALPHA" else "ALPHA",), rubric="Same agent retains latest saved instruction; no stale prefix")
            for limit in ("Одно предложение без списков.", "Ровно три коротких пункта: название, цена, срок возврата."):
                self.question(f"format-{scenario}-{'one' if limit.startswith('Одно') else 'three'}", scenario, "Расскажи об условиях Luma.", rules=[limit, "Не выдумывай факты."], rubric=limit+" Preserve731 KZT and14days when mentioned.")

    def temperature(self):
        question = "Кратко пригласи меня узнать больше о Luma: назови цену и возможность возврата, выбери естественную формулировку. Без новых обещаний."
        for scenario in ("inbox", "crm"):
            conversation = self.lab.conversation(question)[0] if scenario == "inbox" else None
            for temperature in (0.1, 0.8):
                saved = self.lab.configure(scenario, temperature=temperature, tone="friendly")
                for repeat in range(12):
                    self.run(f"temperature-{scenario}-{temperature}-{repeat+1:02}", lambda: self.ask(scenario, question, conversation=conversation), required=("731",), rubric="Repeated identical prompt/context; compare variation separately from truthfulness. No requirement that each sample differ.", settings=saved)

    def scope(self):
        from scripts.ai_behavior.scope_cases import run_scope
        run_scope(self)

    def dialogue(self):
        from scripts.ai_behavior.scope_cases import run_dialogue
        run_dialogue(self)

    def analytics(self):
        from scripts.ai_behavior.action_cases import run_analytics
        run_analytics(self)

    def commands(self):
        from scripts.ai_behavior.action_cases import run_commands
        run_commands(self)

    def pipeline(self):
        from scripts.ai_behavior.action_cases import run_pipeline
        run_pipeline(self)

    def continuity(self):
        from scripts.ai_behavior.continuity_cases import run_continuity
        run_continuity(self)

    def customer_acceptance(self):
        from scripts.ai_behavior.customer_cases import run_customer_acceptance
        run_customer_acceptance(self)

    def final_responses(self):
        for suite in (self.profiles, self.scope, self.dialogue, self.analytics, self.temperature):
            suite()

    def final_crm(self):
        if not self.case_filter:
            self.case_filter = r"(?:-crm-|^sources-)"
        self.question("calendar-crm-local-time", "crm", "Во сколько ближайшая запись по местному времени бизнеса? Укажи только дату и местное время.",
                      required=("15:00",), rubric="Fixture is 2026-10-08 10:00 UTC =15:00 Asia/Almaty; no model timezone arithmetic required")
        for suite in (self.profiles, self.scope, self.dialogue, self.temperature):
            suite()

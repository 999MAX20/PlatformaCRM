"""Prepare replies/proposals and dispatch explicitly requested voice actions."""
from copy import deepcopy
from datetime import date

from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.ai_core.agent_runtime import bind_thread, bind_conversation
from apps.ai_core.assistant import build_crm_context
from apps.ai_core.conversation_access import references_visible, staff_conversation
from apps.ai_core.conversation_copy import conversation_text
from apps.ai_core.conversation_memory import staff_memory
from apps.ai_core.conversation_router import OPERATIONS, resolve_step_target, route_turn
from apps.ai_core.conversation_state import assert_current_turn, fail_turn, locked_conversation
from apps.ai_core.crm_planner import plan_command
from apps.ai_core.ai_client import AIClientError
from apps.ai_core.crm_tools import ENTITIES, prepare_command, read_entities, scoped_entities, serialize_record, target_for_command
from apps.ai_core.models import AgentTurn, AIToolCallLog
from apps.ai_core.services import run_ai_request
from apps.ai_core.workflows import assert_workflow_enabled
from apps.ai_core.voice_policy import validate_voice_plan, validate_voice_proposal


def payload_references(payload):
    references = []
    if payload.get("entity_id"):
        references.append({"entity": payload["entity"], "id": payload["entity_id"]})
    for field, entity in (("client", "clients"), ("lead", "leads"), ("deal", "deals"), ("appointment", "appointments")):
        value = payload.get("values", {}).get(field)
        if type(value) is int:
            references.append({"entity": entity, "id": value})
    client = payload.get("values", {}).get("client")
    if isinstance(client, dict) and type(client.get("id")) is int:
        references.append({"entity": "clients", "id": client["id"]})
    return references


def _completed_context(turn):
    references, results = [], []
    for log in turn.tool_calls.filter(status=AIToolCallLog.Statuses.EXECUTED).order_by("pk"):
        entity, entity_id = log.output_json.get("entity"), log.output_json.get("entity_id")
        if entity in ENTITIES and type(entity_id) is int:
            record = target_for_command(turn.conversation.business, turn.conversation.owner, entity, entity_id)
            references.append({"entity": entity, "id": entity_id})
            results.append({"tool_call_id": log.pk, "entity": entity, "record": serialize_record(ENTITIES[entity], record, turn.conversation.owner)})
    return references, results


def prepare_actions(turn, plan, memory, language):
    thread, user = turn.conversation, turn.conversation.owner
    plan = deepcopy(plan)
    validate_voice_plan(turn.context_json, plan, turn.message)
    if thread.kind == "voice" and any(step["entity"] == "appointments" and step["operation"] == "create" for step in plan["steps"]):
        from apps.ai_core.voice_schedule_planner import prepare_schedule
        # Legacy two-step router output is collapsed before any client write.
        step = next(step for step in plan["steps"] if step["entity"] == "appointments")
        plan["steps"] = [{**step, "after": None, "request": turn.message}]
        return prepare_schedule(turn, plan, memory, language)
    references, completed = _completed_context(turn)
    memory = {**memory, "completed_actions": completed}
    prepared = []
    question = ""
    for index, step in enumerate(plan["steps"]):
        turn.refresh_from_db(fields=["status", "memory_epoch"])
        assert_current_turn(staff_conversation(conversation_id=thread.pk, user=user, write=True), turn)
        existing = turn.tool_calls.filter(pk=step.get("tool_call_id")).first() if step.get("tool_call_id") else None
        if existing and existing.status in {AIToolCallLog.Statuses.EXECUTED, AIToolCallLog.Statuses.SUGGESTED}:
            step["completed"] = existing.status == AIToolCallLog.Statuses.EXECUTED
            continue
        parent = plan["steps"][step["after"]] if step.get("after") is not None else None
        if parent and not parent.get("completed"):
            break  # Its concrete result will require a separate reviewed proposal.
        if parent and step["operation"] != "create" and not step.get("target_id") and not step.get("query"):
            parent_log = turn.tool_calls.get(pk=parent["tool_call_id"])
            if parent_log.output_json.get("entity") == step["entity"]:
                step["target_id"] = parent_log.output_json.get("entity_id")
        target_id, question, found = resolve_step_target(thread=thread, user=user, step=step, language=language)
        references.extend(found)
        if question:
            break
        result = plan_command(business=thread.business, user=user, entity=step["entity"], entity_id=target_id,
                              message=step["request"], conversation_memory=memory, persist=False,
                              expected_tool=OPERATIONS[step["operation"]], source_message=turn.message)
        question = result["question"]
        if question:
            break
        proposal = result["prepared_command"]
        validate_voice_proposal(turn.context_json, proposal["tool"], proposal["payload"])
        references.extend(payload_references(proposal["payload"]))
        prepared.append({"step": index, **proposal})
    return {"plan": plan, "prepared": prepared, "references": references, "question": question,
            "response": question or conversation_text("review", language),
            "status": AgentTurn.Statuses.CLARIFYING if question else AgentTurn.Statuses.AWAITING_CONFIRMATION}


def prepare_answer(turn, plan, memory, language):
    thread, user = turn.conversation, turn.conversation.owner
    if plan["intent"] == "analytics":
        from apps.ai_core.history import explain_history
        result = explain_history(business=thread.business, user=user, start=date.fromisoformat(plan["period"]["start"]),
                                 end=date.fromisoformat(plan["period"]["end"]), question=turn.message, conversation_memory=memory)
        return {"response": result["answer"] or conversation_text("no_data", language), "sources": result["sources"],
                "request_log_id": result.get("log_id"), "context": {"provider_state": result["provider_state"], "period": plan["period"]}}
    context = build_crm_context(thread.business, user=user)
    answer_contract = None
    if plan.get("read"):
        entity = plan["read"]["entity"]
        found = read_entities(business=thread.business, user=user, entity=entity, query=plan["read"].get("query", ""))
        key = {"leads": "latest_leads", "appointments": "upcoming_appointments"}.get(entity, entity)
        context[key] = found["results"]
        context["summary"]["search"] = {"entity": entity, "query": plan["read"].get("query", ""),
                                         "count": found["count"], "shown": len(found["results"]), "has_more": found["has_more"],
                                         "total_count": scoped_entities(thread.business, user, entity).count(),
                                         "coverage": "permitted_non_archived_records"}
        answer_contract = (
            " summary.search.total_count is the total of all currently permitted non-archived records of that entity, without the search filter."
            " summary.search.count is only the number matching query; shown is the bounded page size, never a total."
            " A question asking for both a total and a named record needs both facts: give total_count as the overall count,"
            " then explicitly label count as matching the search and identify the record. Never replace the overall count with count or shown."
            " Cite CRM-summary for these counters and entity sources for record details. These current counters are not historical period totals."
        )
    result, log = run_ai_request(business=thread.business, user=user, prompt_type="crm_assistant", user_input=turn.message,
                                input_json={"crm_context": context, "conversation_memory": memory}, response_language=language,
                                response_contract=answer_contract)
    prefixes = {"CLIENT": "clients", "LEAD": "leads", "DEAL": "deals", "TASK": "tasks", "APPOINTMENT": "appointments"}
    references = []
    for source in result.sources:
        prefix, _, value = source["id"].partition("-")
        if prefix in prefixes and value.isdigit():
            references.append({"entity": prefixes[prefix], "id": int(value)})
    return {"response": result.output_text, "sources": result.sources, "references": references,
            "request_log_id": log.pk, "context": {"provider_state": result.provider_state}}


def _commit_preparation(turn_id, user, result):
    thread_id = AgentTurn.objects.values_list("conversation_id", flat=True).get(pk=turn_id)
    with locked_conversation(thread_id, user) as thread:
        turn = thread.turns.get(pk=turn_id)
        assert_current_turn(thread, turn)
        references = result.get("references", [])
        if not references_visible(thread=thread, user=user, references=references):
            raise PermissionDenied("A referenced record is no longer available.")
        plan = result.get("plan", {})
        for proposal in result.get("prepared", []):
            payload = proposal["payload"]
            validate_voice_proposal(turn.context_json, proposal["tool"], payload)
            current = prepare_command(business=thread.business, user=user, tool=proposal["tool"],
                payload={key: value for key, value in payload.items() if key in {"entity", "entity_id", "values", "action", "reason"}})
            if current.get("expected_version") != payload.get("expected_version"):
                raise PermissionDenied("CRM record changed. Request a fresh proposal.")
            log = AIToolCallLog.objects.create(business=thread.business, user=user, tool_name=proposal["tool"], input_json=payload)
            turn.tool_calls.add(log)
            plan["steps"][proposal["step"]]["tool_call_id"] = log.pk
        turn.plan_json = plan
        turn.response = result.get("response", "")
        turn.status = result.get("status", AgentTurn.Statuses.COMPLETED)
        turn.sources_json = result.get("sources", [])
        turn.references_json = list({(item["entity"], item["id"]): item for item in references}.values())
        turn.context_json = {**turn.context_json, **result.get("context", {}), "question": result.get("question", "")}
        turn.request_log_id = result.get("request_log_id")
        turn.error_code = ""
        turn.completed_at = timezone.now() if turn.status == AgentTurn.Statuses.COMPLETED else None
        turn.save()
        thread.save(update_fields=["updated_at"])
        next_job = None
        if turn.context_json.get("execution") == "direct" and turn.status == AgentTurn.Statuses.AWAITING_CONFIRMATION:
            from apps.ai_core.conversation_actions import confirm_turn
            from apps.ai_core.tool_registry import tool_call_fingerprint
            actions = [{"id": log.pk, "fingerprint": tool_call_fingerprint(log)}
                       for log in turn.tool_calls.filter(status=AIToolCallLog.Statuses.SUGGESTED)]
            turn, next_job = confirm_turn(conversation_id=thread.pk, turn_id=turn.pk, user=user,
                actions=actions, expected_revision=turn.sequence, _direct=True)
        return turn, next_job


def prepare_agent_turn(turn_id):
    turn = AgentTurn.objects.select_related("conversation__business", "conversation__agent", "conversation__owner").get(pk=turn_id)
    if turn.status != AgentTurn.Statuses.PREPARING:
        return {"turn_id": turn.pk, "status": turn.status}
    try:
        thread = staff_conversation(conversation_id=turn.conversation_id, user=turn.conversation.owner, write=True)
        turn.conversation = thread
        with bind_thread(thread), bind_conversation(thread.pk):
            assert_current_turn(thread, turn)
            config = assert_workflow_enabled(thread.business, "analyst" if turn.mode == "analytics" else "employee")
            language = config.get("language", "ru")
            if thread.kind == "voice":
                language = getattr(getattr(thread.owner, "preferences", None), "language", "ru")
                if language not in {"ru", "kk", "en"}:
                    language = "ru"
            memory = staff_memory(thread=thread, user=thread.owner, query=turn.message, before_sequence=turn.sequence)
            if turn.plan_json.get("steps"):
                plan = turn.plan_json  # Resume only the unfinished steps of this turn.
            elif not config["sources"]:
                plan = {"intent": "answer", "steps": [], "read": None, "period": None}
            else:
                for attempt in range(2 if turn.mode == "analytics" else 1):
                    turn.refresh_from_db(fields=["status", "memory_epoch"])
                    assert_current_turn(staff_conversation(conversation_id=thread.pk, user=thread.owner, write=True), turn)
                    try:
                        plan, _ = route_turn(thread=thread, user=thread.owner, message=turn.message, memory=memory,
                            context=turn.context_json, mode=turn.mode, language=language, format_retry=bool(attempt))
                        break
                    except AIClientError as exc:
                        if turn.mode != "analytics" or attempt or exc.error_code != "invalid_action_plan":
                            raise
            turn.refresh_from_db(fields=["status", "memory_epoch"])
            assert_current_turn(staff_conversation(conversation_id=thread.pk, user=thread.owner, write=True), turn)
            if plan["intent"] == "actions" and turn.mode == "analytics":
                result = {"response": conversation_text("analytics_read_only", language), "status": AgentTurn.Statuses.COMPLETED}
            elif plan["intent"] == "actions":
                result = prepare_actions(turn, plan, memory, language)
            elif plan["intent"] in {"greeting", "chat"} and thread.kind == "voice":
                from apps.ai_core.voice_chat import prepare_voice_chat
                result = {**prepare_voice_chat(turn, language), "plan": plan}
            elif plan["intent"] == "greeting":
                result = {"response": conversation_text("greeting", language), "plan": plan}
            elif plan["intent"] == "clarify":
                result = {"response": plan["question"], "question": plan["question"], "status": AgentTurn.Statuses.CLARIFYING, "plan": plan}
            elif plan["intent"] == "cancel":
                result = {"response": conversation_text("cancelled", language), "status": AgentTurn.Statuses.CANCELLED, "plan": plan}
            else:
                result = {**prepare_answer(turn, plan, memory, language), "plan": plan}
            saved, next_job = _commit_preparation(turn.pk, thread.owner, result)
            if next_job is not None:
                from apps.ai_core.conversation_state import dispatch_conversation_job
                dispatch_conversation_job(next_job)
                saved.refresh_from_db()
            return {"turn_id": saved.pk, "status": saved.status}
    except Exception as exc:
        code = "access_changed" if isinstance(exc, PermissionDenied) else "provider_unavailable"
        if isinstance(exc, PermissionDenied) and str(exc.detail) in {"voice_action_unavailable", "voice_one_operation"}:
            code = str(exc.detail)
        if getattr(exc, "error_code", "") in {"invalid_action_plan", "invalid_sources", "planner_unavailable", "rate_limited", "action_failed"}:
            code = exc.error_code
        fail_turn(turn_id, code)
        raise

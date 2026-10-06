import logging
import uuid

from django.conf import settings
from django.db.models import F, Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.ai_core.ai_client import generate_text
from apps.ai_core.agent_runtime import agent_binding, bind_agent
from apps.ai_core.context_service import get_business_knowledge_context
from apps.ai_core.models import AIJob, AIRequestLog
from apps.ai_core.prompt_service import build_prompt
from apps.ai_core.grounding import ANSWER_CONTRACT, source_catalog, validate_answer
from apps.ai_core.assistant import assert_business_access, build_crm_context
from apps.businesses.access import Actions, Resources, assert_can
from apps.billing.models import UsageCounter
from apps.billing.entitlements import EntitlementMetrics, assert_entitlement_allows
from apps.billing.usage import increment_usage


logger = logging.getLogger(__name__)


def run_ai_request(
    *,
    business,
    prompt_type,
    user_input,
    source=AIRequestLog.Sources.CRM,
    user=None,
    input_json=None,
    allow_mock=True,
    model=None,
    model_tier=None,
    temperature=None,
    response_language=None,
    response_contract=None,
):
    assert_entitlement_allows(business, EntitlementMetrics.AI_REQUESTS)
    runtime_context = dict(input_json or {})
    scenario = "analyst" if prompt_type in {"business_event_analyst", "business_history_analyst"} else "employee" if prompt_type in {"crm_assistant", "daily_summary", "crm_action_plan"} else None
    scenario_config = None
    if source == AIRequestLog.Sources.CRM and scenario:
        from apps.ai_core.workflows import assert_workflow_enabled, workflow_fingerprint
        scenario_config = assert_workflow_enabled(business, scenario)
        fingerprint = workflow_fingerprint(business, scenario)
        response_language = scenario_config.get("language") or response_language
        runtime_context["saved_scenario"] = scenario_config
        model = scenario_config.get("model") or model
        model_tier = scenario_config.get("model_tier") or model_tier
        if scenario_config.get("temperature") is not None:
            temperature = scenario_config["temperature"]
        user_input = f"Saved style: {scenario_config.get('tone', 'expert')}. {scenario_config.get('instructions', '')}\n{user_input}"
    inbound = [item.get("text", "") for item in runtime_context.get("messages", []) if isinstance(item, dict) and item.get("direction") == "inbound"]
    from apps.ai_core.knowledge import available_agent
    agent_id = runtime_context.get("bot_id") if source == AIRequestLog.Sources.BOT else (scenario_config or {}).get("agent_id")
    knowledge_agent = available_agent(business=business, agent_id=agent_id) if agent_id else None
    context = get_business_knowledge_context(business, query=inbound[-1] if inbound else user_input, agent=knowledge_agent)
    if scenario_config and "knowledge" not in scenario_config["sources"]:
        context = []
    grounded = source == AIRequestLog.Sources.CRM and "crm_context" in runtime_context
    sources = source_catalog(runtime_context.get("crm_context"), context) if grounded else []
    if grounded:
        runtime_context["source_catalog"] = sources
    agent_preferences = None
    escalation_rules = None
    if scenario_config:
        agent_preferences = {"role": scenario_config.get("role", ""), "instructions": scenario_config.get("instructions", ""),
                             "rules": scenario_config.get("rules", {}).get("items", []), "tone": scenario_config.get("tone")}
    elif prompt_type in {"bot_suggest_reply", "conversation_qualification"} and knowledge_agent is not None:
        from apps.ai_core.models import AgentProfile
        profile = AgentProfile.objects.filter(business=business, bot=knowledge_agent, is_active=True).order_by("-updated_at").first()
        if profile is not None and prompt_type == "bot_suggest_reply":
            agent_preferences = {"role": profile.role_description, "instructions": profile.system_prompt,
                                 "rules": profile.rules_json.get("items", []), "tone": profile.tone}
        elif profile is not None:
            escalation_rules = profile.escalation_rules_json.get("items", [])
    prompt = build_prompt(prompt_type=prompt_type, user_input=user_input, context=context, runtime_context=runtime_context,
                          response_language=response_language, agent_preferences=agent_preferences, escalation_rules=escalation_rules)
    if grounded:
        prompt.messages[0]["content"] += ANSWER_CONTRACT
    if response_contract:
        prompt.messages[0]["content"] += response_contract
    language_name = {"ru": "Russian", "kk": "Kazakh", "en": "English"}.get(response_language)
    if language_name:
        prompt.messages[0]["content"] += (
            f" Output language requirement: write all human-readable response text, including the JSON answer field, in {language_name}."
            " Keep schema keys, source IDs, entity names and codes unchanged. The question's language does not change this requirement."
        )
    result = generate_text(
        prompt,
        prompt_type=prompt_type,
        model=model,
        model_tier=model_tier,
        temperature=temperature,
        allow_mock=allow_mock,
    )
    if scenario_config and workflow_fingerprint(business, scenario) != fingerprint:
        raise PermissionDenied("AI scenario configuration changed while preparing the answer.")
    if knowledge_agent is not None:
        current_agent = available_agent(business=business, agent_id=knowledge_agent.pk)
        current_context = get_business_knowledge_context(business, query=inbound[-1] if inbound else user_input, agent=current_agent)
        if scenario_config and "knowledge" not in scenario_config["sources"]:
            current_context = []
        if current_context != context:
            raise PermissionDenied("Agent knowledge changed while preparing the answer. Please retry.")
    if grounded:
        result = validate_answer(result, sources)
    log = AIRequestLog.objects.create(
        business=business,
        user=user,
        source=source,
        prompt_type=prompt_type,
        input_json={
            "user_input": user_input,
            "context": context,
            "ai_provider": result.provider,
            "ai_model_tier": model_tier,
            "ai_temperature": temperature,
            "ai_response_language": response_language,
            "provider_state": result.provider_state,
            "sources": result.sources,
            **(input_json or {}),
            **({"_agent": agent_binding(business)} if scenario_config else {}),
        },
        output_text=result.output_text,
        model=result.model,
        tokens_used=result.tokens_used,
    )
    increment_usage(business, UsageCounter.Metrics.AI_REQUESTS)
    return result, log


def create_ai_job(
    *,
    business,
    user,
    prompt_type,
    user_input,
    source=AIRequestLog.Sources.CRM,
    input_json=None,
    idempotency_key=None,
):
    input_json = dict(input_json or {})
    if source == AIRequestLog.Sources.CRM:
        input_json["_agent"] = agent_binding(business)
    key = idempotency_key or uuid.uuid4().hex
    job, created = AIJob.objects.get_or_create(
        business=business,
        idempotency_key=key,
        defaults={
            "user": user,
            "source": source,
            "prompt_type": prompt_type,
            "input_json": {"user_input": user_input, "runtime_context": input_json or {}},
        },
    )
    if created:
        from apps.ai_core.tasks import process_ai_job_task

        process_ai_job_task.apply_async(args=[job.id], queue="ai")
    elif job.user_id != getattr(user, "id", None):
        raise PermissionDenied()
    elif (job.prompt_type != prompt_type or job.input_json.get("user_input") != user_input
          or (job.input_json.get("runtime_context") or {}).get("_agent", {}) != input_json.get("_agent", {})):
        raise ValidationError("This request key has already been used for a different request.")
    return job, created


def process_due_ai_jobs(*, limit=100):
    now = timezone.now()
    # A dead worker may have reached the paid provider. End the abandoned
    # attempt visibly; only an explicit new user request may repeat that call.
    cutoff = now - timezone.timedelta(seconds=max(300, settings.AI_HTTP_TIMEOUT_SECONDS * 3))
    expired = AIJob.objects.filter(status=AIJob.Statuses.RUNNING).filter(
        Q(locked_at__lte=cutoff) | Q(locked_at__isnull=True, updated_at__lte=cutoff)
    ).update(
        status=AIJob.Statuses.FAILED,
        error="AI request was interrupted. Please retry or continue manually.",
        locked_at=None, next_retry_at=None, completed_at=now, updated_at=now,
    )
    if expired:
        logger.warning("ai.jobs_interrupted", extra={"expired_jobs": expired})
    job_ids = list(
        AIJob.objects.filter(
            Q(status=AIJob.Statuses.PENDING)
            | Q(status=AIJob.Statuses.RETRY_SCHEDULED, next_retry_at__lte=now)
        )
        .order_by("created_at")
        .values_list("id", flat=True)[:limit]
    )
    return [process_ai_job(job_id) for job_id in job_ids]


def process_ai_job(job_id):
    now = timezone.now()
    claimed = (
        AIJob.objects.filter(id=job_id)
        .filter(
            Q(status=AIJob.Statuses.PENDING)
            | Q(status=AIJob.Statuses.RETRY_SCHEDULED, next_retry_at__lte=now)
        )
        .update(
            status=AIJob.Statuses.RUNNING,
            attempts=F("attempts") + 1,
            locked_at=now,
            next_retry_at=None,
            error="",
            updated_at=now,
        )
    )
    if not claimed:
        return AIJob.objects.filter(id=job_id).first()
    job = AIJob.objects.select_related("business", "user").get(id=job_id)
    if job.status != AIJob.Statuses.RUNNING or job.locked_at != now:
        return job
    claim = AIJob.objects.filter(
        pk=job.pk, status=AIJob.Statuses.RUNNING, attempts=job.attempts, locked_at=now,
    )
    try:
        runtime_context = job.input_json.get("runtime_context") or {}
        with bind_agent(runtime_context.get("_agent", {}).get("agent_id")):
            if runtime_context.get("_agent") and runtime_context["_agent"] != agent_binding(job.business):
                raise PermissionDenied("Agent settings changed. Submit a new request.")
            if job.source == AIRequestLog.Sources.CRM:
                assert_business_access(job.user, job.business)
                assert_can(job.user, job.business, Resources.AI_ASSISTANT, Actions.SUGGEST)
                runtime_context = {"crm_context": build_crm_context(job.business, user=job.user)}
            result, log = run_ai_request(
                business=job.business,
                user=job.user,
                source=job.source,
                prompt_type=job.prompt_type,
                user_input=job.input_json.get("user_input", ""),
                input_json=runtime_context,
                allow_mock=False,
            )
        result_json = {
            "answer": result.output_text,
            "provider": result.provider,
            "model": result.model,
            "tokens_used": result.tokens_used,
            "log_id": log.id,
            "is_mock": result.is_mock,
            "provider_state": result.provider_state,
            "sources": result.sources,
            "context": runtime_context.get("crm_context", {}).get("summary", {}),
        }
        updates = {
            "status": AIJob.Statuses.SUCCEEDED, "result_json": result_json,
            "request_log": log, "completed_at": timezone.now(), "locked_at": None,
        }
    except Exception as exc:
        logger.warning("ai.job_failed", extra={"ai_job_id": job.id, "error_type": type(exc).__name__})
        updates = {"error": "AI request could not be completed. Please retry or continue manually.", "locked_at": None}
        if job.attempts < job.max_attempts and getattr(exc, "retryable", not isinstance(exc, (PermissionError, PermissionDenied, ValidationError))):
            delay_seconds = min(3600, 60 * (2 ** max(job.attempts - 1, 0)))
            updates.update(status=AIJob.Statuses.RETRY_SCHEDULED, next_retry_at=timezone.now() + timezone.timedelta(seconds=delay_seconds))
        else:
            updates.update(status=AIJob.Statuses.FAILED, completed_at=timezone.now())
    # Recovery can expire this attempt while its provider call is outstanding.
    # A late answer/error must not replace the failed state or schedule a retry.
    claim.update(**updates, updated_at=timezone.now())
    job.refresh_from_db()
    return job

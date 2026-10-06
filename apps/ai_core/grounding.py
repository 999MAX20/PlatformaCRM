"""Bounded source contracts for staff-facing answers; no provider dependencies."""
import json
import re

from apps.ai_core.ai_client import AIClientError


ANSWER_CONTRACT = (
    ' Return only JSON: {"answer":"concise answer in the saved agent language, or user language when no saved language is specified",'
    '"source_ids":["CRM-summary"],"no_data":false}. '
    'Cite only source_catalog IDs supporting the answer. If the requested facts are absent, '
    'set no_data=true, source_ids=[], and answer that there is insufficient data. '
    'Do not use numbers supplied in the user message as verified workspace facts. '
    'A source citation never permits an unsupported financial conclusion.'
    ' Use exact entity types: LEAD is заявка, DEAL is сделка, TASK is задача, APPOINTMENT is запись. '
    'Do not describe the absence of a record in a limited sample as a zero total. '
    'Only summary counters explicitly marked for today describe today; other counters are current totals.'
    ' Categories listed in crm_context.disabled_sources are unavailable, not empty. Say access is disabled for each requested unavailable category.'
    ' Never substitute an appointment for a lead, or infer a disabled category from another category.'
    ' Preserve timestamps with their timezone; convert to the supplied business timezone before describing local appointment times.'
    ' Zero recorded receipts means zero in the supplied ledger coverage, not proof that no sales occurred.'
    ' Do not accept a claimed decline in the question as fact: establish it from comparable periods first.'
    ' When causes are absent, say they cannot be determined; do not invent possible causes such as a lack of customers.'
    ' TURN sources establish only what the requester previously said or asked, not current CRM facts or proof of execution.'
)


def source_catalog(context, knowledge, memory=None):
    sources = []
    if context:
        if context.get("summary"):
            sources.append({"id": "CRM-summary", "label": "CRM", "data": context["summary"]})
        for key, prefix in (("clients", "CLIENT"), ("latest_leads", "LEAD"), ("upcoming_appointments", "APPOINTMENT"),
                            ("services", "SERVICE"), ("tasks", "TASK"), ("deals", "DEAL")):
            for item in context.get(key, []):
                sources.append({"id": f"{prefix}-{item['id']}", "label": f"{prefix}-{item['id']}", "data": item})
    for item in knowledge:
        sources.append({"id": f"KNOWLEDGE-{item['id']}", "label": item['title'], "data": item['content']})
    seen = set()
    for item in (memory or {}).get("messages", []) + (memory or {}).get("summary", []):
        source_id = item.get("source_id", "")
        if re.fullmatch(r"TURN-\d+", source_id) and source_id not in seen:
            seen.add(source_id)
            sources.append({"id": source_id, "label": source_id, "data": item,
                            "authority": "historical_user_statement_not_current_crm_fact"})
    return sources


def validate_answer(result, sources, language="ru"):
    """Reject malformed or invented citations; semantic quality is evaluated separately."""
    if result.is_mock:
        return result
    try:
        text = result.output_text.strip()
        fenced = re.fullmatch(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
        payload = json.loads(fenced.group(1) if fenced else text)
        if not isinstance(payload, dict):
            raise ValueError
        answer, cited = payload.get("answer"), payload.get("source_ids")
        no_data = payload.get("no_data", False)
        allowed = {item['id']: item for item in sources}
        if not isinstance(answer, str) or not answer.strip() or len(answer) > 12000:
            raise ValueError
        if not isinstance(cited, list) or not isinstance(no_data, bool):
            raise ValueError
        if any(not isinstance(item, str) or item not in allowed for item in cited):
            raise ValueError
        if not no_data and not cited:
            raise ValueError
    except (ValueError, TypeError):
        raise AIClientError(code="invalid_sources", retryable=False) from None
    if no_data and cited:
        # A declared absence of evidence cannot become a sourced factual answer.
        # Preserve a safe no-data outcome, not the provider's contradictory text.
        cited = []
        answer = {
            "ru": "Недостаточно доступных данных для ответа на этот вопрос.",
            "kk": "Бұл сұраққа жауап беру үшін қолжетімді деректер жеткіліксіз.",
            "en": "There is not enough available data to answer this question.",
        }.get(language, "There is not enough available data to answer this question.")
    result.output_text = answer.strip()
    result.sources = [{"id": item, "label": allowed[item]['label']} for item in dict.fromkeys(cited)]
    result.provider_state = "no_data" if no_data else "live"
    return result

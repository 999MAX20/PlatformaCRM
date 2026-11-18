from copy import deepcopy


PATCH_CONTRACT = '''When draft is nonempty, a short answer or correction normally updates it.
For such a continuation return ONLY {"patch":{},"visits":[]} instead of a full schedule.
patch may contain client_name, client_phone or client_id. visits contains objects
with index (one-based visit position) and only changed fields from the visit schema.
Omitted fields stay exactly as previously supplied. Do not repeat unchanged fields.
Do not add/delete/reorder visits or change plan. For one visit use index=1;
for multiple visits change only an explicitly identified visit or all if explicitly requested.
"Нет, на завтра" changes date only; "Әсел емес, Әсем" changes client_name only.
"Другой специалист" without a name clears specialist to "" and any_resource to false
so the server asks for that field; it does NOT authorize any available specialist.
A time change must include time_text quoted exactly from the latest answer.
Uncertain corrected values should be cleared for a focused clarification, never guessed.
Only a clearly separate NEW booking request may use the original full schedule schema.
Never carry the old person's client_id when correcting their name or phone.
'''


def pending_schedule(turn, memory):
    pending = memory.get("pending", {})
    if (pending.get("turn_id") == turn.context_json.get("schedule_parent")
            and pending.get("state") in {"clarifying", "superseded"}):
        return pending.get("schedule_draft", {})
    return {}


def apply_schedule_patch(previous, value, message):
    if not previous or set(value) != {"patch", "visits"}:
        raise ValueError
    changes, visits = value["patch"], value["visits"]
    if not isinstance(changes, dict) or set(changes) - {"client_name", "client_phone", "client_id"}:
        raise ValueError
    if not isinstance(visits, list) or len(visits) > len(previous["visits"]):
        raise ValueError
    draft = deepcopy(previous)
    draft.update(changes)
    if {"client_name", "client_phone"} & changes.keys() and "client_id" not in changes:
        draft["client_id"] = None
    seen = set()
    for patch in visits:
        if not isinstance(patch, dict):
            raise ValueError
        index = patch.get("index")
        if type(index) is not int or not 1 <= index <= len(draft["visits"]) or index in seen:
            raise ValueError
        seen.add(index)
        fields = {key: val for key, val in patch.items() if key != "index"}
        if set(fields) - set(draft["visits"][index - 1]):
            raise ValueError
        if fields.get("time") or "time_basis" in fields:
            evidence = fields.get("time_text")
            if not isinstance(evidence, str) or not evidence.strip() or " ".join(evidence.split()).casefold() not in " ".join(message.split()).casefold():
                raise ValueError
        if "specialist" in fields and "any_resource" not in fields:
            fields["any_resource"] = False
        draft["visits"][index - 1].update(fields)
    return draft

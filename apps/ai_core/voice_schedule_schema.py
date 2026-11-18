"""Provider structure for full schedules and bounded pending-draft changes."""


def _object(properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def schedule_schema(has_draft):
    text = {"type": "string"}
    visit = {field: text for field in ("date", "time", "time_text", "time_basis", "service", "specialist", "branch")}
    visit["any_resource"] = {"type": "boolean"}
    client = {"client_name": text, "client_phone": text, "client_id": {"type": ["integer", "null"]}}
    full = _object({**client, "plan": {"type": "boolean"}, "visits": {"type": "array", "items": _object(visit)}})
    if not has_draft:
        return _object({"schedule": full})
    nullable = lambda fields: {key: {"type": [value["type"], "null"]}
                              if isinstance(value["type"], str) else value for key, value in fields.items()}
    patch = _object({"patch": _object(nullable(client)), "visits": {"type": "array", "items": _object({
        "index": {"type": "integer"}, **nullable(visit)})}})
    return _object({"schedule": {"anyOf": [patch, full]}})


SCHEMA_CONTRACT = '''Wrap the final response in exactly {"schedule": <schedule or patch>}.
In a patch, nullable fields are null when unchanged; empty strings explicitly clear
uncertain values. Client fields belong ONLY in patch, never in visits. Every visit
patch has an integer index. For a new booking use the full schedule inside schedule.
'''

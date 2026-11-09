from datetime import date
from decimal import Decimal, InvalidOperation

from apps.core.import_export import CLIENT_FIELD_ALIASES, CATALOG_FIELD_ALIASES, guess_mapping
from .schema import FIELDS


ALIASES = {
    "clients": CLIENT_FIELD_ALIASES,
    "services": CATALOG_FIELD_ALIASES,
    "specialists": {
        "name": ["name", "имя", "фио", "специалист", "specialist", "аты"],
        "profession": ["profession", "профессия", "специализация", "мамандық"],
        "contact_phone": ["phone", "телефон", "contact_phone"],
        "public_description": ["description", "описание", "сипаттама"],
    },
    "appointments": {
        "client_ref": ["client_id", "client_ref", "код клиента"],
        "service_ref": ["service_id", "service_ref", "код услуги"],
        "specialist_ref": ["specialist_id", "specialist_ref", "код специалиста"],
        "start_at": ["start_at", "datetime", "дата и время", "басталу уақыты"],
        "status": ["status", "статус", "мәртебе"],
        "notes": ["notes", "комментарий", "заметки", "ескертпе"],
        "reason": ["reason", "причина", "себеп"],
    },
}


def suggest_mapping(headers, entity_type):
    aliases = {key: ALIASES[entity_type].get(key, [key]) for key in FIELDS[entity_type]}
    aliases["external_id"] = ["external_id", "id", "код", "идентификатор"]
    return guess_mapping(headers, aliases)


def suggest_type(values):
    values = [value.strip() for value in values if value.strip()]
    if not values:
        return "text"
    if all(value.lower() in {"true", "false", "да", "нет", "yes", "no"} for value in values):
        return "boolean"
    try:
        if all(Decimal(value).is_finite() and not (len(value) > 1 and value.startswith("0") and not value.startswith("0.")) for value in values):
            return "number"
    except InvalidOperation:
        pass
    try:
        if all(len(value) == 10 and date.fromisoformat(value) for value in values):
            return "date"
    except ValueError:
        pass
    return "text"

"""Agent purpose is persisted in existing settings and immutable through public writes."""
from rest_framework.exceptions import ValidationError

from apps.bots.models import Bot
from apps.businesses.models import Business


def _validate_settings(settings, scenario):
    if "_deleted_at" in settings:
        raise ValidationError({"settings_json": "Agent deletion is managed by its lifecycle endpoint."})
    if scenario not in Bot.Scenarios.values:
        raise ValidationError({"scenario": "Select inbox or crm."})
    if scenario == Bot.Scenarios.CRM and (
        settings.get("auto_crm_pipeline") or settings.get("_automatic_actor_id")
    ):
        raise ValidationError({"settings_json": "CRM assistants cannot enable customer-channel automation."})


def prepare_creation(data):
    data = dict(data)
    settings = dict(data.get("settings_json") or {})
    scenario = data.pop("scenario", settings.get("scenario", Bot.Scenarios.INBOX))
    if "scenario" in settings and settings["scenario"] != scenario:
        raise ValidationError({"scenario": "Conflicting agent purpose."})
    _validate_settings(settings, scenario)
    # A shared business lock also serializes concurrent CRM assistant creation.
    Business.objects.select_for_update().get(pk=data["business"].pk)
    if scenario == Bot.Scenarios.CRM and Bot.objects.filter(business=data["business"], settings_json__scenario=scenario).exists():
        raise ValidationError({"scenario": "This business already has a CRM assistant. Open the existing agent."})
    data["settings_json"] = {**settings, "scenario": scenario}
    return data


def prepare_update(bot, data):
    data = dict(data)
    scenario = data.pop("scenario", bot.scenario)
    settings = dict(data.get("settings_json", bot.settings_json) or {})
    if scenario != bot.scenario or settings.get("scenario", bot.scenario) != bot.scenario:
        raise ValidationError({"scenario": "Agent purpose cannot change after creation."})
    if "business" in data and data["business"].pk != bot.business_id:
        raise ValidationError({"business": "An agent cannot move to another business."})
    _validate_settings(settings, scenario)
    if "settings_json" in data:
        data["settings_json"] = {**settings, "scenario": scenario}
    return data

from rest_framework.exceptions import ValidationError

from apps.services.models import Service


def validate_template_metadata(value):
    if not isinstance(value, dict) or set(value) != {"language", "category", "specialty", "services"}:
        raise ValidationError({"metadata": "Provide the template classification fields."})
    if value["language"] not in ("", "ru", "kk", "en"):
        raise ValidationError({"metadata": "Select a supported template language."})
    for field in ("category", "specialty"):
        if not isinstance(value[field], str) or len(value[field]) > 255:
            raise ValidationError({"metadata": "Provide classification text of at most 255 characters."})
    services = value["services"]
    if not isinstance(services, list) or len(services) > 50:
        raise ValidationError({"metadata": "Select at most 50 services."})
    seen = set()
    for service in services:
        if (not isinstance(service, dict) or set(service) != {"id", "name"}
                or type(service["id"]) is not int or service["id"] <= 0 or service["id"] in seen
                or not isinstance(service["name"], str) or not 1 <= len(service["name"]) <= 255):
            raise ValidationError({"metadata": "Provide valid service snapshots."})
        seen.add(service["id"])
    return {**value, "services": [dict(service) for service in services]}


def capture_template_metadata(value, *, business_id):
    if not isinstance(value, dict) or set(value) != {"language", "category", "specialty", "service_ids"}:
        raise ValidationError({"metadata": "Provide language, category, specialty and service_ids."})
    ids = value["service_ids"]
    if (not isinstance(ids, list) or len(ids) > 50
            or any(type(item) is not int or item <= 0 for item in ids) or len(set(ids)) != len(ids)):
        raise ValidationError({"metadata": "Select at most 50 distinct services."})
    services = dict(Service.objects.filter(business_id=business_id, pk__in=ids).values_list("pk", "name"))
    if len(services) != len(ids):
        raise ValidationError({"metadata": "Select services of this business."})
    return validate_template_metadata({key: value[key] for key in ("language", "category", "specialty")} | {
        "services": [{"id": pk, "name": services[pk]} for pk in sorted(ids)]})

from django.apps import apps
from django.utils.module_loading import import_string
from rest_framework.exceptions import ValidationError


def validate_appointment_transition(*, appointment, actor, target):
    for config in apps.get_app_configs():
        validator = getattr(config, "appointment_transition_validator", None)
        if validator:
            import_string(validator)(appointment=appointment, actor=actor, target=target)


def validate_recording_mode(*, mode, **context):
    for config in apps.get_app_configs():
        validator = getattr(config, "appointment_recording_validator", None)
        if validator and import_string(validator)(mode=mode, **context):
            return
    raise ValidationError({"creation_mode": "Unsupported appointment recording mode."})

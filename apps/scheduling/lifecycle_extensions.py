from django.apps import apps
from django.utils.module_loading import import_string


def validate_appointment_transition(*, appointment, actor, target):
    for config in apps.get_app_configs():
        validator = getattr(config, "appointment_transition_validator", None)
        if validator:
            import_string(validator)(appointment=appointment, actor=actor, target=target)

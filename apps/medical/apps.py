from django.apps import AppConfig


class MedicalConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.medical"
    personal_notification_source = "apps.medical.notification_sources.MedicalNotificationSource"
    appointment_transition_validator = "apps.medical.appointment_lifecycle.validate_appointment_transition"

    def ready(self):
        from . import assistant_signals  # noqa: F401

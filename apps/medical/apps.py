from django.apps import AppConfig


class MedicalConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.medical"
    personal_notification_source = "apps.medical.participation_notifications.ParticipationNotificationSource"

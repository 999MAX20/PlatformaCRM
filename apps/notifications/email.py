from django.conf import settings
from django.core.mail import send_mail


def email_is_local_capture():
    return settings.EMAIL_BACKEND in {
        "django.core.mail.backends.locmem.EmailBackend",
        "django.core.mail.backends.console.EmailBackend",
    }


def email_is_configured():
    from apps.core.production_rules import has_transactional_email

    if email_is_local_capture():
        return settings.ENVIRONMENT in {"local", "development", "test"}
    return has_transactional_email()


def send_email_smoke(to_email):
    return send_mail(
        subject=f"PlatformaCRM email smoke: {settings.ENVIRONMENT}/{settings.RELEASE}",
        message="This is a safe PlatformaCRM transactional email smoke message. It contains no merchant or customer data.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to_email],
        fail_silently=False,
    )

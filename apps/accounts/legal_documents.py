"""Technical acknowledgements for the owner-approved empty document pages."""

REQUIRED_DOCUMENT_IDS = ("terms", "privacy", "personal-data", "company-data")


def record_signup_acknowledgements(request, user, document_ids):
    from apps.accounts.auth_views import record_security_event
    from apps.core.models import AuditLog

    record_security_event(
        request, user=user, event="signup_document_acknowledgements",
        risk_level=AuditLog.RiskLevels.LOW,
        metadata={"document_ids": list(document_ids), "content_status": "placeholder"},
    )

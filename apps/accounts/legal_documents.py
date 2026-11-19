"""Technical acknowledgements for the owner-approved empty document pages."""

REQUIRED_DOCUMENT_IDS = ("terms", "privacy", "personal-data", "company-data")


def record_signup_acknowledgements(request, user, document_ids, *, acceptance_method="checkboxes"):
    from apps.accounts.auth_views import record_security_event
    from apps.core.models import AuditLog

    record_security_event(
        request, user=user, event="signup_document_acknowledgements",
        risk_level=AuditLog.RiskLevels.LOW,
        metadata={
            "document_ids": list(document_ids),
            "content_status": "placeholder",
            "acceptance_method": acceptance_method,
            "notice_version": "signup-submit-2026-11-19" if acceptance_method == "signup_submit" else None,
        },
    )

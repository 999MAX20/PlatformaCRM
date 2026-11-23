import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, Throttled

from apps.businesses.models import Business
from .identity_crypto import MedicalDataUnavailable, medical_request_digest
from .issuance_access import active_grant, assert_local_issuance
from .issuance_services import grant_event
from .models import MedicalDocumentGrant, MedicalDocumentPortalAttempt, MedicalDocumentPortalSession, MedicalDocumentCorrection
from .document_content import read_document_revision
from .document_finalization_services import finalization_evidence
from .signing_services import _material


@transaction.atomic
def record_portal_attempt(business_id, address):
    business = Business.objects.select_for_update().get(pk=business_id)
    bucket = medical_request_digest({"portal_address": address}, business_id=business.pk)
    now = timezone.now()
    attempt, _ = MedicalDocumentPortalAttempt.objects.get_or_create(bucket=bucket, defaults={"started_at": now})
    if now - attempt.started_at >= timedelta(minutes=15):
        attempt.started_at, attempt.count = now, 0
    attempt.count += 1
    attempt.save(update_fields=["started_at", "count"])
    return attempt.count <= 30


def login_portal(*, business_slug, code, address):
    assert_local_issuance()
    business = Business.objects.filter(slug=business_slug).first()
    if business is None:
        raise PermissionDenied("The document access is unavailable.")
    if not record_portal_attempt(business.pk, address):
        raise Throttled(wait=900)
    if not isinstance(code, str) or len(code) > 40:
        raise PermissionDenied("The document access is unavailable.")
    normalized = code.replace("-", "").replace(" ", "").upper()
    if len(normalized) != 20 or any(char not in "23456789ABCDEFGHJKLMNPQRSTUVWXYZ" for char in normalized):
        raise PermissionDenied("The document access is unavailable.")
    with transaction.atomic():
        Business.objects.select_for_update().get(pk=business.pk)
        grant = MedicalDocumentGrant.objects.select_related("patient", "representative", "encounter").filter(
            patient__business=business, code_hash=medical_request_digest({"document_code": normalized}, business_id=business.pk)).first()
        if grant is None:
            raise PermissionDenied("The document access is unavailable.")
        active_grant(grant)
        token = secrets.token_urlsafe(32)
        expiry = min(grant.expires_at, timezone.now() + timedelta(minutes=30))
        MedicalDocumentPortalSession.objects.create(grant=grant,
            token_hash=medical_request_digest({"portal_session": token}, business_id=business.pk), expires_at=expiry)
        grant_event(grant, "session_opened")
        return token, expiry


def session_grant(business_slug, token):
    assert_local_issuance()
    if not isinstance(token, str) or not 20 <= len(token) <= 100:
        raise PermissionDenied("The document access is unavailable.")
    business = Business.objects.select_for_update().filter(slug=business_slug).first()
    if business is None:
        raise PermissionDenied("The document access is unavailable.")
    session = MedicalDocumentPortalSession.objects.select_related("grant__patient", "grant__representative", "grant__encounter").filter(
        grant__patient__business=business, expires_at__gt=timezone.now(),
        token_hash=medical_request_digest({"portal_session": token}, business_id=business.pk)).first()
    if session is None:
        raise PermissionDenied("The document access is unavailable.")
    active_grant(session.grant)
    return session.grant, session.expires_at


def final_item(item):
    if item.finalization_id is None or item.finalization.version_id != item.version_id:
        raise MedicalDataUnavailable()
    finalization_evidence(item.finalization)
    return item.finalization


@transaction.atomic
def portal_documents(*, business_slug, token):
    grant, session_expires_at = session_grant(business_slug, token)
    rows = []
    for item in grant.items.select_related("version__document", "finalization__artifact__attachment", "finalization__version__document"):
        final_item(item)
        snapshot = read_document_revision(item.version)
        rows.append({"id": str(item.public_id), "title": snapshot["template"]["title"],
            "revision": item.version.revision,
            "has_correction": MedicalDocumentCorrection.objects.filter(source__version=item.version).exists()})
    grant_event(grant, "pack_opened")
    return {"expires_at": grant.expires_at, "session_expires_at": session_expires_at, "synthetic": True, "documents": rows}


@transaction.atomic
def portal_pdf(*, business_slug, token, public_id, download=False):
    grant, _ = session_grant(business_slug, token)
    item = grant.items.select_related("version__document", "finalization__artifact__attachment", "finalization__version__document").filter(public_id=public_id).first()
    if item is None:
        raise PermissionDenied("The document access is unavailable.")
    content = _material(final_item(item).artifact)
    grant_event(grant, "downloaded" if download else "document_opened", version=item.version)
    return content


@transaction.atomic
def logout_portal(*, business_slug, token):
    if not isinstance(token, str) or not 20 <= len(token) <= 100:
        return
    business = Business.objects.select_for_update().filter(slug=business_slug).first()
    if business:
        MedicalDocumentPortalSession.objects.filter(grant__patient__business=business,
            token_hash=medical_request_digest({"portal_session": token}, business_id=business.pk)).delete()

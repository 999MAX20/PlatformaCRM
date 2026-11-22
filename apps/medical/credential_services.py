from django.core.exceptions import ValidationError as ModelValidationError
from django.db import DatabaseError, transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.businesses.models import Business, BusinessMember
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from .audit import MedicalAuditUnavailable
from .credential_content import append_credential_revision, read_credential_revision, validate_credential_content
from .identity_crypto import medical_request_digest
from .models import MedicalAuditEvent, MedicalCredentialProfile, MedicalCredentialRevision
from .role_access import assert_medical_role_permission


def _identifier(value):
    if type(value) is not int or value <= 0:
        raise ValidationError({"credentials": "Select a valid profile or version."})


def _context(actor, business_id, member_id, *, write=False, workspace=False):
    _identifier(business_id)
    if member_id is not None:
        _identifier(member_id)
    business = Business.objects.select_for_update().filter(pk=business_id).first()
    if business is None:
        raise NotFound()
    context = assert_medical_role_permission(actor, business, "medical_documents", "view")
    if context.kind == "head" and context.scope == "business":
        if write:
            approval = assert_medical_role_permission(actor, business, "medical_documents", "approve")
            if approval.scope != "business":
                raise PermissionDenied()
    elif context.kind != "doctor" or (not workspace and member_id != context.member_id) or write:
        raise PermissionDenied()
    if member_id is not None:
        members = BusinessMember.objects.filter(pk=member_id, business=business)
        if write:
            members = members.filter(is_active=True, user__is_active=True)
        if not members.exists():
            raise NotFound()
    return business, context


@transaction.atomic
def credential_workspace_access(*, actor, business_id):
    business, context = _context(actor, business_id, None, workspace=True)
    can_confirm = False
    if context.kind == "head":
        try:
            approval = assert_medical_role_permission(actor, business, "medical_documents", "approve")
            can_confirm = approval.scope == "business"
        except PermissionDenied:
            pass
    return {"business_id": business.pk, "member_id": context.member_id,
            "kind": context.kind, "actions": {"view": True, "confirm": can_confirm}}


def _page(limit, before):
    if type(limit) is not int or not 1 <= limit <= 50:
        raise ValidationError({"limit": "Select a page size between 1 and 50."})
    if before is not None:
        _identifier(before)


@transaction.atomic
def list_credential_members(*, actor, business_id, before_id=None, limit=20):
    business, _ = _context(actor, business_id, None)
    _page(limit, before_id)
    members = BusinessMember.objects.filter(business=business, is_active=True,
        user__is_active=True).select_related("user").order_by("-pk")
    if before_id is not None:
        members = members.filter(pk__lt=before_id)
    page = list(members[:limit + 1])
    return {"results": [{"id": member.pk, "name": member.user.full_name} for member in page[:limit]],
            "next_before_id": page[limit - 1].pk if len(page) > limit else None}


@transaction.atomic
def list_credential_versions(*, actor, business_id, member_id, before_revision=None, limit=20):
    business, _ = _context(actor, business_id, member_id)
    _page(limit, before_revision)
    versions = MedicalCredentialRevision.objects.filter(profile__business=business,
        profile__member_id=member_id).order_by("-revision")
    if before_revision is not None:
        versions = versions.filter(revision__lt=before_revision)
    page = list(versions[:limit + 1])
    for version in page[:limit]:
        write_credential_audit(actor=actor, business=business, version=version, action="read")
    return {"results": [{"id": version.pk, "revision": version.revision, "author_id": version.author_id,
        "created_at": version.created_at.isoformat(), "confirmed_by_id": version.confirmed_by_id,
        "confirmed_at": version.confirmed_at.isoformat() if version.confirmed_at else None} for version in page[:limit]],
        "next_before_revision": page[limit - 1].revision if len(page) > limit else None}


def write_credential_audit(*, actor, business, version, action):
    if action not in {"read", "credential_confirmed"}:
        raise ValueError("Select a credential audit action.")
    current = MedicalCredentialRevision.objects.select_related("profile").filter(
        pk=version.pk, profile__business=business).first()
    if current is None or current.revision > current.profile.revision:
        raise ValueError("Audit requires a version of this business.")
    try:
        current.profile.clean()
    except ModelValidationError:
        raise ValueError("Audit requires consistent profile links.") from None
    if action == "credential_confirmed" and (current.confirmed_by_id != actor.pk or
            current.confirmed_at is None or current.author_id != actor.pk or
            current.revision != current.profile.revision):
        raise ValueError("Confirmation audit requires the actor's current confirmed version.")
    try:
        event = MedicalAuditEvent.objects.create(business=business, actor=actor,
            credential_version=current, action=action, result="success")
        if event is None or event.pk is None:
            raise MedicalAuditUnavailable()
        return event
    except DatabaseError:
        raise MedicalAuditUnavailable() from None


@transaction.atomic
def confirm_medical_credentials(*, actor, business_id, member_id, content, reason,
                                expected_revision, idempotency_key):
    business, _ = _context(actor, business_id, member_id, write=True)
    if type(expected_revision) is not int or expected_revision < 0:
        raise ValidationError({"expected_revision": "Provide the current revision, or zero for a new profile."})
    if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 128:
        raise ValidationError({"idempotency_key": "Provide an idempotency key of at most 128 characters."})
    content = validate_credential_content(content, clinician=member_id is not None)
    required = ("license",) if member_id is None else ("specialty", "position")
    if any(not content[field].strip() for field in required):
        raise ValidationError({"credentials": "Complete the required credential fields before confirmation."})
    if not isinstance(reason, str) or len(reason) > 2000:
        raise ValidationError({"reason": "Provide a comment of at most 2000 characters."})

    def operation():
        profile = MedicalCredentialProfile.objects.filter(business=business, member_id=member_id).first()
        if expected_revision != (profile.revision if profile else 0):
            raise InvalidTransition("The credentials changed; reload the current version.")
        if profile is None:
            profile = MedicalCredentialProfile.objects.create(business=business, member_id=member_id)
        version = append_credential_revision(profile=profile, author=actor, content=content, reason=reason)
        version.confirmed_by = actor
        version.confirmed_at = timezone.now()
        version.save(update_fields=["confirmed_by", "confirmed_at"])
        write_credential_audit(actor=actor, business=business, version=version, action="credential_confirmed")
        return CRMCommandResult(data={}, status_code=201, resource=version)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.credentials.confirm",
        idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business_id),
        payload={"member_id": member_id, "expected_revision": expected_revision,
            "content_digest": medical_request_digest({"content": content, "reason": reason}, business_id=business_id)},
        operation=operation)
    version = MedicalCredentialRevision.objects.get(profile__business=business,
        pk=result.resource_id if result.replayed else result.resource.pk)
    return version, result.replayed


@transaction.atomic
def read_medical_credentials(*, actor, business_id, member_id, version_id=None):
    business, _ = _context(actor, business_id, member_id)
    if version_id is not None:
        _identifier(version_id)
    profile = MedicalCredentialProfile.objects.filter(business=business, member_id=member_id).first()
    if profile is None:
        if version_id is not None:
            raise NotFound()
        return {"member_id": member_id, "current_revision": 0, "version": None}
    versions = MedicalCredentialRevision.objects.filter(profile=profile)
    version = versions.filter(pk=version_id).first() if version_id is not None else versions.filter(revision=profile.revision).first()
    if version is None:
        raise NotFound()
    snapshot = read_credential_revision(version)
    write_credential_audit(actor=actor, business=business, version=version, action="read")
    return {"member_id": member_id, "current_revision": profile.revision, "version": {
        "id": version.pk, "revision": version.revision, "author_id": version.author_id,
        "created_at": version.created_at.isoformat(), "confirmed_by_id": version.confirmed_by_id,
        "confirmed_at": version.confirmed_at.isoformat() if version.confirmed_at else None, **snapshot}}

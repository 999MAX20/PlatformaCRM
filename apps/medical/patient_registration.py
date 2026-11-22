from django.db import transaction
from django.db.models import Q
from rest_framework.exceptions import ValidationError

from apps.activities.services import create_activity_event
from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.models import Business
from apps.clients.identity import normalize_email, normalize_phone
from apps.clients.models import Client
from apps.clients.serializers import ClientSerializer
from apps.core.audit import write_actor_audit_log
from apps.core.crm_read_scope import readable_queryset
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from apps.core.models import AuditLog
from .identity_crypto import iin_digest, medical_request_digest, normalize_iin
from .models import PatientProfile
from .patient_selectors import reception_context
from .patient_services import _demographics, create_patient_profile


class PatientMatchesRequireReview(InvalidTransition):
    error_code = "patient_matches_require_review"
    default_code = error_code
    default_detail = "Review the permitted possible matches before creating a separate person."


@transaction.atomic
def register_new_patient(*, actor, business_id, branch_id, full_name, phone, email, demographics,
                         iin, confirmed_separate_person, idempotency_key):
    actor, business, branch = reception_context(actor=actor, business_id=business_id, branch_id=branch_id, action="create")
    Business.objects.select_for_update().get(pk=business.pk)
    actor, business, branch = reception_context(actor=actor, business_id=business_id, branch_id=branch_id, action="create")
    assert_can(actor, business, Resources.CLIENTS, Actions.CREATE)
    assert_can(actor, business, Resources.CLIENTS, Actions.VIEW)
    if type(confirmed_separate_person) is not bool:
        raise ValidationError({"confirmed_separate_person": "Confirm whether this is a separate person."})
    if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 128:
        raise ValidationError({"idempotency_key": "Provide an idempotency key of at most 128 characters."})
    serializer = ClientSerializer(data={"business": business.pk, "full_name": full_name, "phone": phone, "email": email},
                                  context={"actor": actor})
    serializer.is_valid(raise_exception=True)
    values = _demographics(demographics, business)
    identifier = normalize_iin(iin) if iin not in (None, "") else None
    digest = iin_digest(identifier, business_id=business.pk) if identifier else None
    client_fields = {key: serializer.validated_data.get(key, "") for key in ("full_name", "phone", "email")}
    fingerprint = medical_request_digest({**client_fields, "demographics": values, "iin": identifier,
        "confirmed_separate_person": confirmed_separate_person}, business_id=business.pk)
    command_key = medical_request_digest({"key": idempotency_key}, business_id=business.pk)

    def operation():
        if digest and PatientProfile.objects.filter(business=business, iin_digest=digest, identity_status="verified").exists():
            raise InvalidTransition("Medical identity requires review before creating another profile.")
        candidates = Q(full_name__iexact=client_fields["full_name"])
        normalized_phone = normalize_phone(client_fields["phone"])
        normalized_email = normalize_email(client_fields["email"])
        if normalized_phone:
            candidates |= Q(normalized_phone=normalized_phone)
        if normalized_email:
            candidates |= Q(normalized_email=normalized_email)
        if digest:
            candidates |= Q(medical_profile__business=business, medical_profile__iin_digest=digest)
        visible = readable_queryset(Client.objects.all(), actor=actor, business=business, resource=Resources.CLIENTS)
        if not confirmed_separate_person and visible.filter(candidates).exists():
            raise PatientMatchesRequireReview()
        client = serializer.save()
        write_actor_audit_log(actor=actor, action=AuditLog.Actions.CREATE, instance=client, business=business)
        create_activity_event(actor=actor, business=business, event_type="client.created", instance=client)
        patient, _ = create_patient_profile(actor=actor, business_id=business.pk, branch_id=branch.pk,
            client_id=client.pk, demographics=values, iin=identifier, idempotency_key=f"registration:{command_key}")
        return CRMCommandResult(data={}, status_code=201, resource=patient)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.patient.register",
        idempotency_key=command_key, payload={"branch": branch.pk, "fingerprint": fingerprint}, operation=operation)
    patient = PatientProfile.objects.get(pk=result.resource_id if result.replayed else result.resource.pk, business=business)
    assert_can(actor, business, Resources.CLIENTS, Actions.VIEW, obj=patient.client)
    return patient, result.replayed

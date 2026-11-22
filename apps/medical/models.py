from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone
import uuid

from apps.businesses.models import TimeStampedModel


class PatientProfile(TimeStampedModel):
    class IdentityStatus(models.TextChoices):
        UNVERIFIED = "unverified", "Unverified"
        VERIFIED = "verified", "Verified"

    business = models.ForeignKey("businesses.Business", on_delete=models.PROTECT, related_name="patient_profiles")
    client = models.OneToOneField("clients.Client", on_delete=models.PROTECT, related_name="medical_profile")
    demographics_encrypted = models.TextField(blank=True, editable=False)
    iin_encrypted = models.TextField(blank=True, editable=False)
    iin_digest = models.CharField(max_length=64, null=True, blank=True, editable=False,
                                 validators=[RegexValidator(r"\A[a-f0-9]{64}\Z")])
    identity_status = models.CharField(max_length=16, choices=IdentityStatus.choices, default=IdentityStatus.UNVERIFIED)
    verification_evidence_encrypted = models.TextField(blank=True, editable=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT,
                                    related_name="verified_patient_profiles")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_patient_profiles")
    revision = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["business", "iin_digest"],
                condition=models.Q(identity_status="verified", iin_digest__isnull=False),
                name="medical_verified_iin_unique"),
            models.CheckConstraint(condition=models.Q(revision__gte=1), name="medical_patient_revision_positive"),
            models.CheckConstraint(
                condition=(models.Q(iin_digest__isnull=True, iin_encrypted="") |
                           (models.Q(iin_digest__isnull=False) & ~models.Q(iin_digest="") & ~models.Q(iin_encrypted=""))),
                name="medical_patient_iin_pair"),
            models.CheckConstraint(
                condition=(models.Q(identity_status="unverified", verified_at__isnull=True, verified_by__isnull=True) |
                           (models.Q(identity_status="verified", verified_at__isnull=False, verified_by__isnull=False) &
                            ~models.Q(verification_evidence_encrypted=""))),
                name="medical_patient_verification_complete"),
        ]

    def clean(self):
        super().clean()
        from apps.clients.models import Client
        if self.client_id and not Client.objects.filter(pk=self.client_id, business_id=self.business_id).exists():
            raise ValidationError({"client": "Select a client of this business."})


class PatientRepresentative(TimeStampedModel):
    patient = models.ForeignKey(PatientProfile, on_delete=models.PROTECT, related_name="representatives")
    representative_client = models.ForeignKey("clients.Client", on_delete=models.PROTECT,
                                             related_name="medical_representations")
    authority_encrypted = models.TextField(editable=False)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                   related_name="verified_medical_representations")
    verified_at = models.DateTimeField()
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT,
                                  related_name="revoked_medical_representations")
    revocation_encrypted = models.TextField(blank=True, editable=False)
    revision = models.PositiveIntegerField(default=1)

    class Meta:
        indexes = [models.Index(fields=["patient", "representative_client"], name="medical_rep_patient_client")]
        constraints = [
            models.CheckConstraint(condition=~models.Q(authority_encrypted=""), name="medical_rep_authority_present"),
            models.CheckConstraint(condition=models.Q(revision__gte=1), name="medical_rep_revision_positive"),
            models.CheckConstraint(condition=models.Q(valid_until__isnull=True) | models.Q(valid_until__gt=models.F("valid_from")),
                                   name="medical_rep_valid_period"),
            models.CheckConstraint(condition=(
                models.Q(revoked_at__isnull=True, revoked_by__isnull=True, revocation_encrypted="") |
                (models.Q(revoked_at__isnull=False, revoked_by__isnull=False, revoked_at__gte=models.F("verified_at")) &
                 ~models.Q(revocation_encrypted=""))), name="medical_rep_revocation_complete"),
        ]

    def clean(self):
        super().clean()
        from apps.clients.models import Client
        patient = PatientProfile.objects.filter(pk=self.patient_id).values("business_id", "client_id").first()
        if patient and self.representative_client_id == patient["client_id"]:
            raise ValidationError({"representative_client": "Select a person other than the patient."})
        if not patient or not Client.objects.filter(pk=self.representative_client_id, business_id=patient["business_id"]).exists():
            raise ValidationError({"representative_client": "Select a client of the patient's business."})


class PatientIdentityRevision(models.Model):
    patient = models.ForeignKey(PatientProfile, on_delete=models.PROTECT, related_name="identity_revisions")
    revision = models.PositiveIntegerField()
    snapshot_encrypted = models.TextField(editable=False)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                   related_name="patient_identity_revisions")
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["patient", "revision"], name="medical_identity_revision_unique"),
            models.CheckConstraint(condition=models.Q(revision__gte=1), name="medical_identity_revision_positive"),
            models.CheckConstraint(condition=~models.Q(snapshot_encrypted=""), name="medical_identity_snapshot_present"),
        ]


class PatientIdentityCorrection(TimeStampedModel):
    class States(models.TextChoices):
        PENDING = "pending", "Pending medical review"
        APPLIED = "applied", "Applied"
        REJECTED = "rejected", "Rejected"

    patient = models.ForeignKey(PatientProfile, on_delete=models.PROTECT, related_name="identity_corrections")
    branch = models.ForeignKey("branches.Branch", on_delete=models.PROTECT, related_name="identity_corrections")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                     related_name="requested_identity_corrections")
    source_revision = models.PositiveIntegerField()
    source_client_updated_at = models.DateTimeField()
    proposal_encrypted = models.TextField(editable=False)
    state = models.CharField(max_length=16, choices=States.choices, default=States.PENDING)
    medical_review_required = models.BooleanField()
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT,
                                   related_name="decided_identity_corrections")
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_encrypted = models.TextField(blank=True, editable=False)
    applied_revision = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(source_revision__gte=1), name="medical_correction_source_positive"),
            models.CheckConstraint(condition=~models.Q(proposal_encrypted=""), name="medical_correction_proposal_present"),
            models.CheckConstraint(condition=(
                models.Q(state="pending", decided_by__isnull=True, decided_at__isnull=True,
                         decision_encrypted="", applied_revision__isnull=True, medical_review_required=True) |
                (models.Q(state="rejected", decided_by__isnull=False, decided_at__isnull=False,
                          applied_revision__isnull=True, medical_review_required=True) & ~models.Q(decision_encrypted="")) |
                (models.Q(state="applied", decided_by__isnull=False, decided_at__isnull=False,
                          applied_revision__isnull=False, applied_revision__gt=models.F("source_revision")) & ~models.Q(decision_encrypted=""))
            ), name="medical_correction_state_complete"),
        ]

    def clean(self):
        super().clean()
        from apps.branches.models import Branch
        business_id = PatientProfile.objects.filter(pk=self.patient_id).values_list("business_id", flat=True).first()
        if not business_id or not Branch.objects.filter(pk=self.branch_id, business_id=business_id).exists():
            raise ValidationError({"branch": "Select a branch of the patient's business."})


class MedicalRoleAssignment(TimeStampedModel):
    class Kinds(models.TextChoices):
        DOCTOR = "doctor", "Doctor"
        ASSISTANT = "assistant", "Assistant"
        RECEPTION = "reception", "Reception"
        HEAD = "head", "Medical head or deputy"

    member = models.OneToOneField("businesses.BusinessMember", on_delete=models.PROTECT,
                                  related_name="medical_role_assignment")
    business_role = models.ForeignKey("businesses.BusinessRole", on_delete=models.PROTECT,
                                      related_name="medical_assignments")
    kind = models.CharField(max_length=16, choices=Kinds.choices)
    all_branches = models.BooleanField(default=False)
    branches = models.ManyToManyField("branches.Branch", blank=True, related_name="medical_assignments")
    granted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                   related_name="granted_medical_roles")
    granted_at = models.DateTimeField(default=timezone.now)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revision = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(kind__in=["doctor", "assistant", "reception", "head"]),
                                   name="medical_role_kind_known"),
            models.CheckConstraint(condition=models.Q(revision__gte=1), name="medical_role_revision_positive"),
            models.CheckConstraint(condition=models.Q(revoked_at__isnull=True) | models.Q(revoked_at__gte=models.F("granted_at")),
                                   name="medical_role_revocation_order"),
        ]

    def clean(self):
        super().clean()
        from apps.businesses.models import BusinessMember, BusinessRole
        member = BusinessMember.objects.filter(pk=self.member_id).values("business_id", "user_id").first()
        business_id = member["business_id"] if member else None
        if not business_id or not BusinessRole.objects.filter(pk=self.business_role_id, business_id=business_id).exists():
            raise ValidationError({"business_role": "Select a role of the member's business."})
        if self.granted_by_id == member["user_id"]:
            raise ValidationError({"granted_by": "Medical authority cannot be self-granted."})


class MedicalRoleRevision(models.Model):
    assignment = models.ForeignKey(MedicalRoleAssignment, on_delete=models.PROTECT, related_name="decisions")
    revision = models.PositiveIntegerField()
    action = models.CharField(max_length=8, choices=[("grant", "Grant"), ("revoke", "Revoke")])
    reason_encrypted = models.TextField(editable=False)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                             related_name="medical_role_decisions")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["assignment", "revision"], name="medical_role_revision_unique"),
            models.CheckConstraint(condition=models.Q(revision__gte=1), name="medical_role_decision_positive"),
            models.CheckConstraint(condition=models.Q(action__in=["grant", "revoke"]), name="medical_role_revision_action"),
            models.CheckConstraint(condition=~models.Q(reason_encrypted=""), name="medical_role_revision_reason"),
        ]


class TreatmentParticipation(TimeStampedModel):
    class States(models.TextChoices):
        PENDING = "pending", "Pending acceptance"
        ACTIVE = "active", "Active"
        DECLINED = "declined", "Declined"
        WITHDRAWN = "withdrawn", "Withdrawn"
        ENDED = "ended", "Ended"
        REVOKED = "revoked", "Revoked"

    patient = models.ForeignKey(PatientProfile, on_delete=models.PROTECT, related_name="participations")
    member = models.ForeignKey("businesses.BusinessMember", on_delete=models.PROTECT,
                               related_name="treatment_participations")
    branch = models.ForeignKey("branches.Branch", on_delete=models.PROTECT, related_name="treatment_participations")
    state = models.CharField(max_length=16, choices=States.choices, default=States.PENDING)
    proposed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                    related_name="proposed_treatment_participations")
    proposed_at = models.DateTimeField(default=timezone.now)
    source_appointment = models.ForeignKey("scheduling.Appointment", on_delete=models.PROTECT,
        null=True, blank=True, editable=False, related_name="medical_participation_proposals")
    source_participation = models.ForeignKey("self", on_delete=models.PROTECT,
        null=True, blank=True, editable=False, related_name="derived_proposals")
    accepted_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
                                  related_name="closed_treatment_participations")
    reason_encrypted = models.TextField(blank=True, editable=False)
    closure_reason_encrypted = models.TextField(blank=True, editable=False)
    decline_reason_encrypted = models.TextField(blank=True, editable=False)
    work_direction_encrypted = models.TextField(blank=True, editable=False)
    planned_work_date = models.DateField(null=True, blank=True)
    remaining_responsible = models.ForeignKey("businesses.BusinessMember", on_delete=models.PROTECT,
        null=True, blank=True, related_name="closed_medical_participations")
    revision = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["patient", "member", "branch"],
                condition=models.Q(state__in=["pending", "active"]), name="medical_participation_open"),
            models.CheckConstraint(condition=models.Q(revision__gte=1), name="medical_participation_revision"),
            models.CheckConstraint(condition=(models.Q(source_appointment__isnull=True) |
                models.Q(source_participation__isnull=True)), name="medical_participation_one_source"),
            models.CheckConstraint(condition=~models.Q(source_participation=models.F("pk")),
                name="medical_participation_not_self"),
            models.CheckConstraint(condition=(
                models.Q(state="pending", accepted_at__isnull=True, closed_at__isnull=True, closed_by__isnull=True) |
                models.Q(state="active", accepted_at__isnull=False, closed_at__isnull=True, closed_by__isnull=True) |
                models.Q(state__in=["declined", "withdrawn"], accepted_at__isnull=True,
                         closed_at__isnull=False, closed_by__isnull=False) |
                models.Q(state__in=["ended", "revoked"], accepted_at__isnull=False,
                         closed_at__isnull=False, closed_by__isnull=False)), name="medical_participation_state"),
            models.CheckConstraint(condition=(models.Q(accepted_at__isnull=True) |
                models.Q(accepted_at__gte=models.F("proposed_at"))), name="medical_participation_accept"),
            models.CheckConstraint(condition=(models.Q(closed_at__isnull=True) |
                (models.Q(closed_at__gte=models.F("proposed_at")) &
                 (models.Q(accepted_at__isnull=True) | models.Q(closed_at__gte=models.F("accepted_at"))))),
                name="medical_participation_close"),
        ]

    def clean(self):
        super().clean()
        from apps.branches.models import Branch
        from apps.businesses.models import BusinessMember
        patient = PatientProfile.objects.filter(pk=self.patient_id).values("business_id", "client__business_id").first()
        if patient is None or patient["business_id"] != patient["client__business_id"]:
            raise ValidationError({"patient": "Select a patient in this business."})
        business_id = patient["business_id"]
        if not self._state.adding:
            previous_source = TreatmentParticipation.objects.filter(pk=self.pk).values_list(
                "source_appointment_id", "source_participation_id").first()
            if previous_source != (self.source_appointment_id, self.source_participation_id):
                raise ValidationError({"source_appointment": "The original proposal source cannot be changed."})
        if self._state.adding and self.source_appointment_id is not None:
            from apps.scheduling.models import Appointment
            if not Appointment.objects.filter(pk=self.source_appointment_id, business_id=business_id,
                    client__medical_profile__pk=self.patient_id,
                    resource__business_id=business_id, resource__linked_user_id=self.proposed_by_id).exists():
                raise ValidationError({"source_appointment": "Select the proposer's appointment for this patient."})
        if self._state.adding and self.source_participation_id is not None and not TreatmentParticipation.objects.filter(
                pk=self.source_participation_id, patient_id=self.patient_id,
                member__business_id=business_id, member__user_id=self.proposed_by_id,
                branch__business_id=business_id).exclude(pk=self.pk).exists():
            raise ValidationError({"source_participation": "Select the proposer's participation for this patient."})
        if not BusinessMember.objects.filter(pk=self.member_id, business_id=business_id).exists():
            raise ValidationError({"member": "Select a member of the patient's business."})
        if not Branch.objects.filter(pk=self.branch_id, business_id=business_id).exists():
            raise ValidationError({"branch": "Select a branch of the patient's business."})
        if self.remaining_responsible_id is not None and not BusinessMember.objects.filter(
                pk=self.remaining_responsible_id, business_id=business_id).exists():
            raise ValidationError({"remaining_responsible": "Select a member of the patient's business."})


class MedicalParticipationNotice(models.Model):
    notification = models.OneToOneField("notifications.Notification", on_delete=models.CASCADE,
        related_name="medical_participation_notice")
    event = models.OneToOneField("MedicalAuditEvent", on_delete=models.PROTECT,
        related_name="participation_notice")


class MedicalAuditEvent(models.Model):
    class Actions(models.TextChoices):
        PATIENT_CREATED = "patient_created", "Patient created"
        PATIENT_UPDATED = "patient_updated", "Patient updated"
        IDENTITY_VERIFIED = "identity_verified", "Identity verified"
        IDENTITY_CORRECTION_REQUESTED = "identity_correction_requested", "Identity correction requested"
        IDENTITY_CORRECTION_APPLIED = "identity_correction_applied", "Identity correction applied"
        IDENTITY_CORRECTION_REJECTED = "identity_correction_rejected", "Identity correction rejected"
        REPRESENTATIVE_VERIFIED = "representative_verified", "Representative verified"
        REPRESENTATIVE_REVOKED = "representative_revoked", "Representative revoked"
        PARTICIPATION_PROPOSED = "participation_proposed", "Participation proposed"
        PARTICIPATION_ACCEPTED = "participation_accepted", "Participation accepted"
        PARTICIPATION_DECLINED = "participation_declined", "Participation declined"
        PARTICIPATION_WITHDRAWN = "participation_withdrawn", "Participation withdrawn"
        PARTICIPATION_ENDED = "participation_ended", "Participation ended"
        RECORD_OPENED = "record_opened", "Medical record opened"
        ENCOUNTER_OPENED = "encounter_opened", "Encounter opened"
        ENCOUNTER_DRAFT_SAVED = "encounter_draft_saved", "Encounter draft saved"
        TOOTH_OBSERVATION_SAVED = "tooth_observation_saved", "Tooth observation saved"
        DOCUMENT_DRAFT_CREATED = "document_draft_created", "Document draft created"
        DOCUMENT_DRAFT_SAVED = "document_draft_saved", "Document draft saved"
        TEMPLATE_DRAFT_CREATED = "template_draft_created", "Template draft created"
        TEMPLATE_DRAFT_SAVED = "template_draft_saved", "Template draft saved"
        TEMPLATE_SUBMITTED = "template_submitted", "Template submitted"
        TEMPLATE_APPROVED = "template_approved", "Template approved"
        TEMPLATE_REJECTED = "template_rejected", "Template rejected"
        CREDENTIAL_CONFIRMED = "credential_confirmed", "Credential confirmed"
        TEMPLATE_ACTIVATED = "template_activated", "Template activated"
        TEMPLATE_DEACTIVATED = "template_deactivated", "Template deactivated"
        READ = "read", "Read"
        ACCESS_DENIED = "access_denied", "Access denied"

    event_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    business = models.ForeignKey("businesses.Business", on_delete=models.PROTECT, related_name="medical_audit_events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="medical_audit_events")
    patient = models.ForeignKey(PatientProfile, on_delete=models.PROTECT, null=True, blank=True, related_name="audit_events")
    patient_revision = models.PositiveIntegerField(null=True, blank=True)
    identity_correction = models.ForeignKey(PatientIdentityCorrection, on_delete=models.PROTECT,
                                            null=True, blank=True, related_name="audit_events")
    representative = models.ForeignKey(PatientRepresentative, on_delete=models.PROTECT, null=True, blank=True,
                                       related_name="audit_events")
    representative_revision = models.PositiveIntegerField(null=True, blank=True)
    participation = models.ForeignKey(TreatmentParticipation, on_delete=models.PROTECT, null=True, blank=True,
                                      related_name="audit_events")
    participation_revision = models.PositiveIntegerField(null=True, blank=True)
    record = models.ForeignKey("DentalMedicalRecord", on_delete=models.PROTECT, null=True, blank=True,
                               related_name="audit_events")
    encounter_version = models.ForeignKey("MedicalEncounterRevision", on_delete=models.PROTECT, null=True, blank=True,
                                          related_name="audit_events")
    tooth_history = models.ForeignKey("DentalToothHistory", on_delete=models.PROTECT, null=True, blank=True,
                                      related_name="audit_events")
    document_version = models.ForeignKey("MedicalDocumentRevision", on_delete=models.PROTECT, null=True, blank=True,
                                         related_name="audit_events")
    template_version = models.ForeignKey("MedicalDocumentTemplateRevision", on_delete=models.PROTECT,
                                         null=True, blank=True, related_name="audit_events")
    credential_version = models.ForeignKey("MedicalCredentialRevision", on_delete=models.PROTECT,
                                           null=True, blank=True, related_name="audit_events")
    template_availability = models.ForeignKey("MedicalTemplateAvailabilityRevision", on_delete=models.PROTECT,
                                              null=True, blank=True, related_name="audit_events")
    action = models.CharField(max_length=32, choices=Actions.choices)
    result = models.CharField(max_length=16, choices=[("success", "Success"), ("denied", "Denied")])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["business", "patient", "created_at"], name="medical_audit_patient_time")]
        constraints = [
            models.CheckConstraint(
                condition=(models.Q(patient__isnull=True, patient_revision__isnull=True) |
                           models.Q(patient__isnull=False, patient_revision__isnull=False, patient_revision__gte=1)),
                name="medical_audit_patient_version"),
            models.CheckConstraint(
                condition=(models.Q(action="access_denied", result="denied") |
                           models.Q(action__in=["patient_created", "patient_updated", "identity_verified", "read",
                                               "representative_verified", "representative_revoked",
                                               "participation_proposed", "participation_accepted",
                                               "participation_declined", "participation_withdrawn", "participation_ended",
                                               "encounter_opened", "encounter_draft_saved", "record_opened",
                                               "tooth_observation_saved", "document_draft_created",
                                               "document_draft_saved", "template_draft_created",
                                               "template_draft_saved", "template_submitted", "template_approved",
                                               "template_rejected", "credential_confirmed", "template_activated",
                                               "template_deactivated", "identity_correction_requested",
                                               "identity_correction_applied", "identity_correction_rejected"], result="success")),
                name="medical_audit_action_result"),
            models.CheckConstraint(condition=(
                models.Q(representative__isnull=True, representative_revision__isnull=True) |
                models.Q(representative__isnull=False, representative_revision__gte=1,
                         representative_revision__isnull=False, patient__isnull=False)),
                name="medical_audit_rep_version"),
            models.CheckConstraint(condition=(
                models.Q(action__in=["representative_verified", "representative_revoked"], representative__isnull=False) |
                ~models.Q(action__in=["representative_verified", "representative_revoked"])),
                name="medical_audit_rep_required"),
            models.CheckConstraint(condition=(
                models.Q(participation__isnull=True, participation_revision__isnull=True) |
                models.Q(participation__isnull=False, participation_revision__gte=1,
                         participation_revision__isnull=False, patient__isnull=False)),
                name="medical_audit_part_version"),
            models.CheckConstraint(condition=(
                models.Q(action__in=["participation_proposed", "participation_accepted", "participation_declined",
                                     "participation_withdrawn", "participation_ended"], participation__isnull=False) |
                ~models.Q(action__in=["participation_proposed", "participation_accepted", "participation_declined",
                                      "participation_withdrawn", "participation_ended"])), name="medical_audit_part_required"),
            models.CheckConstraint(condition=models.Q(participation__isnull=True) | models.Q(representative__isnull=True),
                                   name="medical_audit_single_relation"),
            models.CheckConstraint(condition=(models.Q(encounter_version__isnull=True) |
                models.Q(patient__isnull=False, representative__isnull=True, participation__isnull=True)),
                name="medical_audit_encounter_patient"),
            models.CheckConstraint(condition=(
                models.Q(action__in=["encounter_opened", "encounter_draft_saved"], encounter_version__isnull=False) |
                ~models.Q(action__in=["encounter_opened", "encounter_draft_saved"])),
                name="medical_audit_encounter_needed"),
            models.CheckConstraint(condition=(models.Q(record__isnull=True) |
                models.Q(patient__isnull=False, representative__isnull=True, participation__isnull=True,
                         encounter_version__isnull=True)), name="medical_audit_record_patient"),
            models.CheckConstraint(condition=(models.Q(action="record_opened", record__isnull=False) |
                ~models.Q(action="record_opened")), name="medical_audit_record_needed"),
            models.CheckConstraint(condition=(models.Q(tooth_history__isnull=True) |
                models.Q(patient__isnull=False, representative__isnull=True, participation__isnull=True,
                         encounter_version__isnull=True, record__isnull=True,
                         action__in=["read", "tooth_observation_saved"])), name="medical_audit_tooth_relation"),
            models.CheckConstraint(condition=(~models.Q(action="tooth_observation_saved") |
                models.Q(tooth_history__isnull=False)), name="medical_audit_tooth_needed"),
            models.CheckConstraint(condition=(models.Q(document_version__isnull=True) |
                models.Q(patient__isnull=False, representative__isnull=True, participation__isnull=True,
                         encounter_version__isnull=True, record__isnull=True, tooth_history__isnull=True,
                         action__in=["read", "document_draft_created", "document_draft_saved"])),
                name="medical_audit_document_relation"),
            models.CheckConstraint(condition=(~models.Q(action__in=["document_draft_created", "document_draft_saved"]) |
                models.Q(document_version__isnull=False)), name="medical_audit_document_needed"),
            models.CheckConstraint(condition=(models.Q(template_version__isnull=True) |
                models.Q(patient__isnull=True, representative__isnull=True, participation__isnull=True,
                         encounter_version__isnull=True, record__isnull=True, tooth_history__isnull=True,
                         document_version__isnull=True,
                         action__in=["read", "template_draft_created", "template_draft_saved",
                                     "template_submitted", "template_approved", "template_rejected",
                                     "template_activated", "template_deactivated"])),
                name="medical_audit_template_relation"),
            models.CheckConstraint(condition=(~models.Q(action__in=["template_draft_created", "template_draft_saved",
                                                                   "template_submitted", "template_approved", "template_rejected"]) |
                models.Q(template_version__isnull=False)), name="medical_audit_template_needed"),
            models.CheckConstraint(condition=(models.Q(credential_version__isnull=True) |
                models.Q(patient__isnull=True, representative__isnull=True, participation__isnull=True,
                         encounter_version__isnull=True, record__isnull=True, tooth_history__isnull=True,
                         document_version__isnull=True, template_version__isnull=True,
                         action__in=["read", "credential_confirmed"])), name="medical_audit_credential_scope"),
            models.CheckConstraint(condition=(~models.Q(action="credential_confirmed") |
                models.Q(credential_version__isnull=False)), name="medical_audit_credential_needed"),
            models.CheckConstraint(condition=(models.Q(template_availability__isnull=True) |
                models.Q(template_version__isnull=False, credential_version__isnull=True,
                         patient__isnull=True, representative__isnull=True, participation__isnull=True,
                         encounter_version__isnull=True, record__isnull=True, tooth_history__isnull=True,
                         document_version__isnull=True, action__in=["read", "template_activated", "template_deactivated"])),
                name="medical_audit_availability_scope"),
            models.CheckConstraint(condition=(~models.Q(action__in=["template_activated", "template_deactivated"]) |
                models.Q(template_availability__isnull=False)), name="medical_audit_availability_needed"),
        ]

class DentalMedicalRecord(TimeStampedModel):
    class States(models.TextChoices):
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    business = models.ForeignKey("businesses.Business", on_delete=models.PROTECT, related_name="dental_records")
    patient = models.ForeignKey(PatientProfile, on_delete=models.PROTECT, related_name="dental_records")
    number = models.CharField(max_length=64)
    state = models.CharField(max_length=16, choices=States.choices, default=States.ACTIVE)
    opened_at = models.DateTimeField(default=timezone.now)
    opened_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="opened_dental_records")
    archived_at = models.DateTimeField(null=True, blank=True)
    archived_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
                                    related_name="archived_dental_records")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["business", "number"], name="medical_record_number_unique"),
            models.UniqueConstraint(fields=["business", "patient"], condition=models.Q(state="active"),
                                    name="medical_record_active_unique"),
            models.CheckConstraint(condition=~models.Q(number=""), name="medical_record_number_present"),
            models.CheckConstraint(condition=(
                models.Q(state="active", archived_at__isnull=True, archived_by__isnull=True) |
                models.Q(state="archived", archived_at__isnull=False, archived_by__isnull=False,
                         archived_at__gte=models.F("opened_at"))), name="medical_record_archive_state"),
        ]

    def clean(self):
        super().clean()
        if not PatientProfile.objects.filter(pk=self.patient_id, business_id=self.business_id,
                                              client__business_id=self.business_id).exists():
            raise ValidationError({"patient": "Select a patient of this business."})
        if not self.number.strip():
            raise ValidationError({"number": "Provide the medical record number."})


class MedicalEncounter(TimeStampedModel):
    class States(models.TextChoices):
        DRAFT = "draft", "Draft"
        FINALIZED = "finalized", "Finalized"

    business = models.ForeignKey("businesses.Business", on_delete=models.PROTECT, related_name="medical_encounters")
    patient = models.ForeignKey(PatientProfile, on_delete=models.PROTECT, related_name="encounters")
    record = models.ForeignKey(DentalMedicalRecord, on_delete=models.PROTECT, related_name="encounters")
    appointment = models.OneToOneField("scheduling.Appointment", on_delete=models.PROTECT, related_name="medical_encounter")
    branch = models.ForeignKey("branches.Branch", on_delete=models.PROTECT, related_name="medical_encounters")
    primary_clinician = models.ForeignKey("businesses.BusinessMember", on_delete=models.PROTECT,
                                        related_name="primary_medical_encounters")
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    state = models.CharField(max_length=16, choices=States.choices, default=States.DRAFT)
    finalized_at = models.DateTimeField(null=True, blank=True)
    finalized_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
                                     related_name="finalized_medical_encounters")
    revision = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(revision__gte=1), name="medical_encounter_revision"),
            models.CheckConstraint(condition=(
                models.Q(state="draft", ended_at__isnull=True, finalized_at__isnull=True, finalized_by__isnull=True) |
                models.Q(state="finalized", ended_at__isnull=False, finalized_at__isnull=False,
                         finalized_by__isnull=False, ended_at__gte=models.F("started_at"),
                         finalized_at__gte=models.F("ended_at"))), name="medical_encounter_state"),
        ]

    def clean(self):
        super().clean()
        from apps.branches.models import Branch
        from apps.businesses.models import BusinessMember
        from apps.scheduling.models import Appointment
        patient = PatientProfile.objects.filter(pk=self.patient_id, business_id=self.business_id,
            client__business_id=self.business_id).values("client_id").first()
        if patient is None:
            raise ValidationError({"patient": "Select a patient of this business."})
        if not DentalMedicalRecord.objects.filter(pk=self.record_id, business_id=self.business_id, patient_id=self.patient_id).exists():
            raise ValidationError({"record": "Select this patient's medical record."})
        if not Appointment.objects.filter(pk=self.appointment_id, business_id=self.business_id,
                client_id=patient["client_id"], branch_id=self.branch_id, service__business_id=self.business_id).exists():
            raise ValidationError({"appointment": "Select an appointment for this patient and branch."})
        if not Branch.objects.filter(pk=self.branch_id, business_id=self.business_id).exists():
            raise ValidationError({"branch": "Select a branch of this business."})
        if not BusinessMember.objects.filter(pk=self.primary_clinician_id, business_id=self.business_id).exists():
            raise ValidationError({"primary_clinician": "Select a clinician of this business."})


class MedicalEncounterRevision(models.Model):
    encounter = models.ForeignKey(MedicalEncounter, on_delete=models.PROTECT, related_name="clinical_revisions")
    revision = models.PositiveIntegerField()
    content_encrypted = models.TextField(editable=False)
    reason_encrypted = models.TextField(blank=True, editable=False)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="medical_encounter_revisions")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["encounter", "revision"], name="medical_encounter_version_unique"),
            models.CheckConstraint(condition=models.Q(revision__gte=1), name="medical_encounter_ver_positive"),
            models.CheckConstraint(condition=~models.Q(content_encrypted=""), name="medical_encounter_ver_content"),
        ]


class MedicalCredentialProfile(TimeStampedModel):
    business = models.ForeignKey("businesses.Business", on_delete=models.PROTECT,
                                 related_name="medical_credential_profiles")
    member = models.ForeignKey("businesses.BusinessMember", on_delete=models.PROTECT,
                               null=True, blank=True, related_name="medical_credential_profiles")
    revision = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["business"], condition=models.Q(member__isnull=True),
                                    name="medical_clinic_credentials_unique"),
            models.UniqueConstraint(fields=["business", "member"], condition=models.Q(member__isnull=False),
                                    name="medical_member_credentials_unique"),
        ]

    def clean(self):
        super().clean()
        from apps.businesses.models import BusinessMember
        if self.member_id is not None and not BusinessMember.objects.filter(
                pk=self.member_id, business_id=self.business_id).exists():
            raise ValidationError({"member": "Select a member of this business."})


class MedicalCredentialRevision(models.Model):
    profile = models.ForeignKey(MedicalCredentialProfile, on_delete=models.PROTECT, related_name="versions")
    revision = models.PositiveIntegerField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                              related_name="medical_credential_versions")
    content_encrypted = models.TextField(editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True, related_name="confirmed_medical_credentials")
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["profile", "revision"], name="medical_credential_version_unique"),
            models.CheckConstraint(condition=models.Q(revision__gte=1), name="medical_credential_ver_positive"),
            models.CheckConstraint(condition=~models.Q(content_encrypted=""), name="medical_credential_ver_content"),
            models.CheckConstraint(condition=(models.Q(confirmed_by__isnull=True, confirmed_at__isnull=True) |
                models.Q(confirmed_by__isnull=False, confirmed_at__isnull=False)),
                name="medical_credential_confirmation"),
        ]


class MedicalDocumentTemplate(TimeStampedModel):
    business = models.ForeignKey("businesses.Business", on_delete=models.PROTECT,
                                 related_name="medical_document_templates")
    code = models.CharField(max_length=64,
        validators=[RegexValidator(r"^[a-z][a-z0-9_]*$", "Provide a template identifier.")])
    owner_member = models.ForeignKey("businesses.BusinessMember", on_delete=models.PROTECT, null=True, blank=True,
                                     related_name="personal_document_templates")
    revision = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    availability_revision = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["business", "code"], name="medical_template_code_unique"),
            models.CheckConstraint(condition=~models.Q(code=""), name="medical_template_code_present"),
        ]

    def clean(self):
        super().clean()
        from apps.businesses.models import BusinessMember
        if self.owner_member_id is not None and not BusinessMember.objects.filter(
                pk=self.owner_member_id, business_id=self.business_id).exists():
            raise ValidationError({"owner_member": "Select a member of this business."})


class MedicalDocumentTemplateRevision(models.Model):
    template = models.ForeignKey(MedicalDocumentTemplate, on_delete=models.PROTECT, related_name="versions")
    revision = models.PositiveIntegerField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                              related_name="medical_template_versions")
    snapshot_encrypted = models.TextField(editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["template", "revision"], name="medical_template_version_unique"),
            models.CheckConstraint(condition=models.Q(revision__gte=1), name="medical_template_ver_positive"),
            models.CheckConstraint(condition=~models.Q(snapshot_encrypted=""), name="medical_template_ver_content"),
        ]


class MedicalTemplateAvailabilityRevision(models.Model):
    template = models.ForeignKey(MedicalDocumentTemplate, on_delete=models.PROTECT, related_name="availability_versions")
    template_version = models.ForeignKey(MedicalDocumentTemplateRevision, on_delete=models.PROTECT,
                                        related_name="availability_changes")
    revision = models.PositiveIntegerField()
    is_active = models.BooleanField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                              related_name="medical_template_availability_changes")
    created_at = models.DateTimeField(auto_now_add=True)
    reason_encrypted = models.TextField(editable=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["template", "revision"], name="medical_template_avail_unique"),
            models.CheckConstraint(condition=models.Q(revision__gte=1), name="medical_template_avail_positive"),
            models.CheckConstraint(condition=~models.Q(reason_encrypted=""), name="medical_template_avail_reason"),
        ]


class MedicalTemplateReview(models.Model):
    class States(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    version = models.OneToOneField(MedicalDocumentTemplateRevision, on_delete=models.PROTECT,
                                   related_name="review")
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                     related_name="submitted_template_reviews")
    submitted_at = models.DateTimeField(auto_now_add=True)
    state = models.CharField(max_length=16, choices=States.choices, default=States.PENDING)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                   null=True, blank=True, related_name="decided_template_reviews")
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_encrypted = models.TextField(editable=False, blank=True, default="")

    class Meta:
        constraints = [models.CheckConstraint(condition=(
            models.Q(state="pending", decided_by__isnull=True, decided_at__isnull=True, decision_encrypted="") |
            (models.Q(state__in=["approved", "rejected"], decided_by__isnull=False,
                      decided_at__isnull=False, decided_at__gte=models.F("submitted_at")) &
             ~models.Q(decision_encrypted=""))), name="medical_template_review_state")]

    def clean(self):
        super().clean()
        from apps.businesses.models import BusinessMember
        if self.version_id:
            business_id = self.version.template.business_id
            for field, user_id in (("submitted_by", self.submitted_by_id), ("decided_by", self.decided_by_id)):
                if user_id is not None and not BusinessMember.objects.filter(business_id=business_id, user_id=user_id).exists():
                    raise ValidationError({field: "Select a member of this business."})


class MedicalDocument(TimeStampedModel):
    business = models.ForeignKey("businesses.Business", on_delete=models.PROTECT, related_name="medical_documents")
    encounter = models.ForeignKey(MedicalEncounter, on_delete=models.PROTECT, related_name="documents")
    template_code = models.CharField(max_length=64,
        validators=[RegexValidator(r"^[a-z][a-z0-9_]*$", "Provide a template identifier.")])
    revision = models.PositiveIntegerField(default=0)
    state = models.CharField(max_length=24, default="draft", choices=[("draft", "Draft")])

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(state="draft"), name="medical_document_draft_only"),
            models.CheckConstraint(condition=~models.Q(template_code=""), name="medical_document_template"),
        ]

    def clean(self):
        super().clean()
        if not MedicalEncounter.objects.filter(pk=self.encounter_id, business_id=self.business_id,
                patient__business_id=self.business_id, patient__client__business_id=self.business_id,
                record__business_id=self.business_id, branch__business_id=self.business_id).exists():
            raise ValidationError({"encounter": "Select an encounter of this business."})


class MedicalDocumentRevision(models.Model):
    document = models.ForeignKey(MedicalDocument, on_delete=models.PROTECT, related_name="versions")
    revision = models.PositiveIntegerField()
    source_version = models.ForeignKey(MedicalEncounterRevision, on_delete=models.PROTECT,
                                      related_name="document_versions")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                              related_name="medical_document_versions")
    snapshot_encrypted = models.TextField(editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["document", "revision"], name="medical_document_version_unique"),
            models.CheckConstraint(condition=models.Q(revision__gte=1), name="medical_document_ver_positive"),
            models.CheckConstraint(condition=~models.Q(snapshot_encrypted=""), name="medical_document_ver_content"),
        ]


FDI_TOOTH_NUMBERS = tuple(quadrant * 10 + position
    for quadrant in range(1, 9)
    for position in range(1, 9 if quadrant <= 4 else 6))


class DentalToothState(TimeStampedModel):
    business = models.ForeignKey("businesses.Business", on_delete=models.PROTECT, related_name="dental_tooth_states")
    patient = models.ForeignKey(PatientProfile, on_delete=models.PROTECT, related_name="tooth_states")
    tooth = models.PositiveSmallIntegerField()
    surface = models.CharField(max_length=32, blank=True, default="",
        validators=[RegexValidator(r"^[a-z][a-z0-9_]*$", "Provide a surface identifier.")])
    revision = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["business", "patient", "tooth", "surface"], name="medical_tooth_location_unique"),
            models.CheckConstraint(condition=models.Q(tooth__in=FDI_TOOTH_NUMBERS), name="medical_tooth_fdi_number"),
            models.CheckConstraint(condition=models.Q(revision__gte=1), name="medical_tooth_revision"),
        ]

    def clean(self):
        super().clean()
        if not PatientProfile.objects.filter(pk=self.patient_id, business_id=self.business_id,
                client__business_id=self.business_id).exists():
            raise ValidationError({"patient": "Select a patient of this business."})


class DentalToothHistory(models.Model):
    tooth_state = models.ForeignKey(DentalToothState, on_delete=models.PROTECT, related_name="history")
    encounter = models.ForeignKey(MedicalEncounter, on_delete=models.PROTECT, related_name="tooth_history")
    revision = models.PositiveIntegerField()
    previous = models.OneToOneField("self", on_delete=models.PROTECT, null=True, blank=True, related_name="next_revision")
    content_encrypted = models.TextField(editable=False)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="dental_tooth_history")
    observed_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tooth_state", "revision"], name="medical_tooth_history_unique"),
            models.CheckConstraint(condition=(models.Q(revision=1, previous__isnull=True) |
                models.Q(revision__gt=1, previous__isnull=False)), name="medical_tooth_history_chain"),
            models.CheckConstraint(condition=~models.Q(content_encrypted=""), name="medical_tooth_history_content"),
        ]
        indexes = [models.Index(fields=["tooth_state", "observed_at", "id"], name="medical_tooth_history_date")]

    def clean(self):
        super().clean()
        state = DentalToothState.objects.filter(pk=self.tooth_state_id).first()
        if state is None:
            raise ValidationError({"tooth_state": "Select an existing tooth state."})
        state.full_clean()
        encounter = MedicalEncounter.objects.filter(pk=self.encounter_id,
            business_id=state.business_id, patient_id=state.patient_id).first()
        if encounter is None:
            raise ValidationError({"encounter": "Select an encounter for this patient and business."})
        encounter.clean()
        if self.revision > state.revision:
            raise ValidationError({"revision": "The tooth revision is not current."})
        if self.previous_id and not DentalToothHistory.objects.filter(pk=self.previous_id,
                tooth_state_id=state.pk, revision=self.revision - 1).exists():
            raise ValidationError({"previous": "Select the preceding revision of this tooth state."})
        from apps.businesses.models import BusinessMember
        if not BusinessMember.objects.filter(business_id=state.business_id, user_id=self.author_id).exists():
            raise ValidationError({"author": "Select an author belonging to this business."})

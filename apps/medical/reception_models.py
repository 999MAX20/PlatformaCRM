from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class ReceptionBookingRequest(models.Model):
    """Organizational follow-up intent; a calendar reservation is a separate action."""

    class States(models.TextChoices):
        NEW = "new", "New"
        PENDING = "pending", "Pending"
        BOOKED = "booked", "Booked"
        DECLINED = "declined", "Declined"
        EXPIRED = "expired", "Could not contact"
        CANCELLED = "cancelled", "Cancelled"

    business = models.ForeignKey("businesses.Business", on_delete=models.PROTECT)
    patient = models.ForeignKey("medical.PatientProfile", on_delete=models.PROTECT)
    source_appointment = models.ForeignKey("scheduling.Appointment", on_delete=models.PROTECT,
        related_name="follow_up_requests")
    branch = models.ForeignKey("branches.Branch", on_delete=models.PROTECT)
    referring_clinician = models.ForeignKey("businesses.BusinessMember", on_delete=models.PROTECT,
        related_name="referred_booking_requests")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="created_reception_requests")
    created_at = models.DateTimeField(default=timezone.now)
    service = models.ForeignKey("services.Service", on_delete=models.PROTECT)
    preferred_resource = models.ForeignKey("scheduling.Resource", on_delete=models.PROTECT)
    recommended_from = models.DateField()
    recommended_until = models.DateField()
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    patient_in_clinic = models.BooleanField(default=False)
    acceptance_due_at = models.DateTimeField(null=True, blank=True)
    state = models.CharField(max_length=12, choices=States.choices, default=States.NEW)
    revision = models.PositiveIntegerField(default=1)
    assignee = models.ForeignKey("businesses.BusinessMember", on_delete=models.PROTECT,
        null=True, blank=True, related_name="assigned_reception_requests")
    claimed_at = models.DateTimeField(null=True, blank=True)
    booked_appointment = models.OneToOneField("scheduling.Appointment", on_delete=models.PROTECT,
        null=True, blank=True, related_name="reception_request")
    closed_at = models.DateTimeField(null=True, blank=True)
    closure_reason = models.CharField(max_length=1000, blank=True)
    contact_cycle = models.PositiveIntegerField(default=1)
    contact_started_at = models.DateTimeField(null=True, blank=True)
    contact_due_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["business", "patient", "source_appointment", "service"],
                condition=models.Q(state__in=["new", "pending"]), name="medical_reception_open"),
            models.CheckConstraint(condition=models.Q(revision__gte=1), name="medical_reception_revision"),
            models.CheckConstraint(condition=models.Q(contact_cycle__gte=1), name="medical_reception_cycle"),
            models.CheckConstraint(condition=models.Q(recommended_until__gte=models.F("recommended_from")),
                name="medical_reception_period"),
            models.CheckConstraint(condition=models.Q(duration_minutes__isnull=True) | models.Q(duration_minutes__gt=0),
                name="medical_reception_duration"),
            models.CheckConstraint(condition=(models.Q(assignee__isnull=True, claimed_at__isnull=True) |
                models.Q(assignee__isnull=False, claimed_at__isnull=False)), name="medical_reception_claim"),
            models.CheckConstraint(condition=(
                models.Q(state__in=["new", "pending"], closed_at__isnull=True, booked_appointment__isnull=True,
                         closure_reason="") |
                models.Q(state="booked", closed_at__isnull=False, booked_appointment__isnull=False) |
                (models.Q(state__in=["declined", "expired", "cancelled"], closed_at__isnull=False,
                          booked_appointment__isnull=True) & ~models.Q(closure_reason=""))),
                name="medical_reception_state"),
        ]

    def clean(self):
        super().clean()
        from apps.branches.models import Branch
        from apps.businesses.models import BusinessMember
        from apps.scheduling.models import Appointment, Resource
        from apps.services.models import Service
        from .models import PatientProfile

        patient = PatientProfile.objects.filter(pk=self.patient_id, business_id=self.business_id,
            client__business_id=self.business_id).first()
        if patient is None:
            raise ValidationError({"patient": "Select a patient of this business."})
        for field, model in (("branch", Branch), ("referring_clinician", BusinessMember),
                             ("service", Service), ("assignee", BusinessMember)):
            identifier = getattr(self, field + "_id")
            if identifier is not None and not model.objects.filter(pk=identifier, business_id=self.business_id).exists():
                raise ValidationError({field: "Select an entity of this business."})
        if not Resource.objects.filter(pk=self.preferred_resource_id, business_id=self.business_id,
                resource_type="staff").exists():
            raise ValidationError({"preferred_resource": "Select a specialist of this business."})
        for field in ("source_appointment", "booked_appointment"):
            identifier = getattr(self, field + "_id")
            if identifier is not None and not Appointment.objects.filter(pk=identifier, business_id=self.business_id,
                    client_id=patient.client_id, service__business_id=self.business_id,
                    branch__business_id=self.business_id).exists():
                raise ValidationError({field: "Select an appointment for this patient and business."})
        if self.booked_appointment_id == self.source_appointment_id:
            raise ValidationError({"booked_appointment": "Select a separate follow-up appointment."})
        if not BusinessMember.objects.filter(business_id=self.business_id, user_id=self.created_by_id).exists():
            raise ValidationError({"created_by": "Select a member of this business."})
        if not self._state.adding:
            fields = ("business_id", "patient_id", "source_appointment_id", "referring_clinician_id",
                      "created_by_id", "created_at")
            previous = type(self).objects.filter(pk=self.pk).values(*fields).first()
            if previous is None or any(previous[field] != getattr(self, field) for field in fields):
                raise ValidationError({"source_appointment": "The original referral cannot be retargeted."})


class ReceptionContactAttempt(models.Model):
    request = models.ForeignKey(ReceptionBookingRequest, on_delete=models.PROTECT, related_name="contact_attempts")
    cycle = models.PositiveIntegerField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)
    outcome = models.CharField(max_length=16, choices=[("no_answer", "No answer"), ("contacted", "Contacted")])
    note = models.CharField(max_length=1000, blank=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(cycle__gte=1, outcome__in=["no_answer", "contacted"]), name="medical_contact_attempt_valid")]

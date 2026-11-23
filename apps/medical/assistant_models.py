from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class AppointmentAssistant(models.Model):
    """An invitation for one appointment, never patient-wide participation."""

    class States(models.TextChoices):
        PENDING = "pending", "Pending acceptance"
        ACTIVE = "active", "Accepted"
        DECLINED = "declined", "Declined"
        REVOKED = "revoked", "Revoked"
        ENDED = "ended", "Appointment basis ended"

    business = models.ForeignKey("businesses.Business", on_delete=models.PROTECT)
    patient = models.ForeignKey("medical.PatientProfile", on_delete=models.PROTECT)
    appointment = models.ForeignKey("scheduling.Appointment", on_delete=models.PROTECT,
                                    related_name="medical_assistants")
    branch = models.ForeignKey("branches.Branch", on_delete=models.PROTECT)
    assignment = models.ForeignKey("medical.MedicalRoleAssignment", on_delete=models.PROTECT,
                                   related_name="assistant_invitations")
    primary_clinician = models.ForeignKey("businesses.BusinessMember", on_delete=models.PROTECT,
                                          related_name="appointment_assistants")
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                   related_name="invited_medical_assistants")
    invited_at = models.DateTimeField(default=timezone.now)
    accepted_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
                                  related_name="closed_assistant_invitations")
    state = models.CharField(max_length=12, choices=States.choices, default=States.PENDING)
    revision = models.PositiveIntegerField(default=1)
    invitation_notification = models.OneToOneField("notifications.Notification", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="medical_assistant_invitation")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["appointment", "assignment"],
                condition=models.Q(state__in=["pending", "active"]), name="medical_assistant_open"),
            models.CheckConstraint(condition=models.Q(revision__gte=1), name="medical_assistant_revision"),
            models.CheckConstraint(condition=(
                models.Q(state="pending", accepted_at__isnull=True, closed_at__isnull=True, closed_by__isnull=True) |
                models.Q(state="active", accepted_at__isnull=False, closed_at__isnull=True, closed_by__isnull=True) |
                models.Q(state="declined", accepted_at__isnull=True, closed_at__isnull=False, closed_by__isnull=False) |
                models.Q(state="revoked", closed_at__isnull=False, closed_by__isnull=False) |
                models.Q(state="ended", closed_at__isnull=False)), name="medical_assistant_state"),
            models.CheckConstraint(condition=(models.Q(accepted_at__isnull=True) |
                models.Q(accepted_at__gte=models.F("invited_at"))), name="medical_assistant_accept_time"),
            models.CheckConstraint(condition=(models.Q(closed_at__isnull=True) |
                (models.Q(closed_at__gte=models.F("invited_at")) &
                 (models.Q(accepted_at__isnull=True) | models.Q(closed_at__gte=models.F("accepted_at"))))),
                name="medical_assistant_close_time"),
        ]

    def clean(self):
        super().clean()
        from apps.branches.models import Branch
        from apps.businesses.models import BusinessMember
        from apps.scheduling.models import Appointment
        from .models import MedicalRoleAssignment, PatientProfile

        patient = PatientProfile.objects.filter(pk=self.patient_id, business_id=self.business_id,
            client__business_id=self.business_id).first()
        if patient is None:
            raise ValidationError({"patient": "Select a patient of this business."})
        if not Appointment.objects.filter(pk=self.appointment_id, business_id=self.business_id,
                client_id=patient.client_id, branch__business_id=self.business_id,
                service__business_id=self.business_id).exists():
            raise ValidationError({"appointment": "Select an appointment for this patient and business."})
        if not Branch.objects.filter(pk=self.branch_id,
                business_id=self.business_id).exists():
            raise ValidationError({"branch": "Select a branch of this business."})
        assignment = MedicalRoleAssignment.objects.filter(pk=self.assignment_id,
            member__business_id=self.business_id, business_role__business_id=self.business_id).first()
        if assignment is None:
            raise ValidationError({"assignment": "Select a medical assignment of this business."})
        if not BusinessMember.objects.filter(pk=self.primary_clinician_id, business_id=self.business_id).exists():
            raise ValidationError({"primary_clinician": "Select a clinician of this business."})
        for field in ("invited_by_id", "closed_by_id"):
            user_id = getattr(self, field)
            if user_id is not None and not BusinessMember.objects.filter(business_id=self.business_id, user_id=user_id).exists():
                raise ValidationError({field: "Select a member of this business."})
        if self._state.adding:
            if assignment.kind != "assistant":
                raise ValidationError({"assignment": "Select an assistant assignment."})
            if not Appointment.objects.filter(pk=self.appointment_id, branch_id=self.branch_id,
                    resource__business_id=self.business_id, resource__resource_type="staff",
                    resource__linked_user_id=self.primary_clinician.user_id).exists():
                raise ValidationError({"primary_clinician": "Select the appointment's current clinician."})
        else:
            fields = ("business_id", "patient_id", "appointment_id", "branch_id", "assignment_id",
                      "primary_clinician_id", "invited_by_id", "invited_at")
            previous = type(self).objects.filter(pk=self.pk).values(*fields).first()
            if previous is None or any(previous[field] != getattr(self, field) for field in fields):
                raise ValidationError({"appointment": "The invitation's original scope cannot be changed."})

from django.db import models

from apps.businesses.models import TimeStampedModel


class Branch(TimeStampedModel):
    business = models.ForeignKey("businesses.Business", on_delete=models.CASCADE, related_name="branches")
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    is_active = models.BooleanField(default=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [models.UniqueConstraint(fields=["business", "name"], name="branch_business_name_unique")]

    def __str__(self):
        return self.name


class BranchAccess(TimeStampedModel):
    member = models.OneToOneField("businesses.BusinessMember", on_delete=models.CASCADE, related_name="branch_access")
    all_branches = models.BooleanField(default=False)
    branches = models.ManyToManyField(Branch, blank=True, related_name="access_grants")


class BranchService(TimeStampedModel):
    business = models.ForeignKey("businesses.Business", on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="service_offers")
    service = models.ForeignKey("services.Service", on_delete=models.PROTECT, related_name="branch_offers")
    price_from = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    duration_minutes = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["service__name", "id"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "service"], name="branch_service_unique"),
            models.CheckConstraint(condition=models.Q(duration_minutes__gt=0, duration_minutes__lte=1440), name="branch_service_duration_valid"),
            models.CheckConstraint(condition=models.Q(price_from__isnull=True) | models.Q(price_from__gte=0), name="branch_service_price_valid"),
        ]


class SpecialistBranch(TimeStampedModel):
    business = models.ForeignKey("businesses.Business", on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="specialist_assignments")
    resource = models.ForeignKey("scheduling.Resource", on_delete=models.PROTECT, related_name="branch_assignments")
    services = models.ManyToManyField("services.Service", blank=True, related_name="specialist_assignments")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["resource__name", "id"]
        constraints = [models.UniqueConstraint(fields=["branch", "resource"], name="branch_specialist_unique")]


class ScheduleDay(TimeStampedModel):
    """One day contains zero or more validated intervals; [] explicitly closes it."""
    business = models.ForeignKey("businesses.Business", on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="schedule_days")
    resource = models.ForeignKey("scheduling.Resource", on_delete=models.PROTECT, null=True, blank=True, related_name="branch_schedule_days")
    weekday = models.PositiveSmallIntegerField(null=True, blank=True)
    date = models.DateField(null=True, blank=True)
    intervals = models.JSONField(default=list)

    class Meta:
        ordering = ["date", "weekday", "id"]
        constraints = [
            models.CheckConstraint(condition=(models.Q(date__isnull=True, weekday__gte=0, weekday__lte=6, weekday__isnull=False)
                                               | models.Q(date__isnull=False, weekday__isnull=True)), name="branch_schedule_day_kind"),
            models.UniqueConstraint(fields=["branch", "resource", "weekday"], condition=models.Q(date__isnull=True, resource__isnull=False), name="branch_staff_weekday_unique"),
            models.UniqueConstraint(fields=["branch", "weekday"], condition=models.Q(date__isnull=True, resource__isnull=True), name="branch_weekday_unique"),
            models.UniqueConstraint(fields=["branch", "resource", "date"], condition=models.Q(date__isnull=False, resource__isnull=False), name="branch_staff_date_unique"),
            models.UniqueConstraint(fields=["branch", "date"], condition=models.Q(date__isnull=False, resource__isnull=True), name="branch_date_unique"),
        ]


class BranchTravelTime(TimeStampedModel):
    business = models.ForeignKey("businesses.Business", on_delete=models.CASCADE)
    from_branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="travel_from")
    to_branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="travel_to")
    minutes = models.PositiveIntegerField()

    class Meta:
        ordering = ["from_branch_id", "to_branch_id"]
        constraints = [
            models.UniqueConstraint(fields=["from_branch", "to_branch"], name="branch_travel_pair_unique"),
            models.CheckConstraint(condition=models.Q(from_branch__lt=models.F("to_branch")), name="branch_travel_order"),
            models.CheckConstraint(condition=models.Q(minutes__lte=1440), name="branch_travel_minutes_valid"),
        ]


class SpecialistAbsence(TimeStampedModel):
    business = models.ForeignKey("businesses.Business", on_delete=models.CASCADE)
    resource = models.ForeignKey("scheduling.Resource", on_delete=models.PROTECT, related_name="absences")
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, null=True, blank=True, related_name="absences")
    starts_on = models.DateField()
    ends_on = models.DateField()
    reason = models.CharField(max_length=24, choices=[("unavailable", "Unavailable"), ("vacation", "Vacation"), ("sick", "Sick")], default="unavailable")

    class Meta:
        ordering = ["-starts_on", "id"]
        constraints = [models.CheckConstraint(condition=models.Q(ends_on__gte=models.F("starts_on")), name="specialist_absence_date_order")]

from django.conf import settings
from django.db import models
from django.utils import timezone


class PurchaseRequest(models.Model):
    business = models.ForeignKey("businesses.Business", on_delete=models.PROTECT)
    branch = models.ForeignKey("branches.Branch", on_delete=models.PROTECT)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    state = models.CharField(max_length=30, default="new")
    revision = models.PositiveIntegerField(default=1)
    urgent = models.BooleanField(default=False)
    needed_by = models.DateField(null=True, blank=True)
    comment = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(revision__gte=1), name="proc_request_revision"),
            models.CheckConstraint(condition=models.Q(urgent=False) | models.Q(needed_by__isnull=False), name="proc_urgent_date"),
        ]
        indexes = [models.Index(fields=["business", "branch", "state", "id"], name="proc_request_queue")]


class PurchaseRequestLine(models.Model):
    request = models.OneToOneField(PurchaseRequest, on_delete=models.PROTECT, related_name="line")
    material = models.CharField(max_length=200)
    specification = models.CharField(max_length=200, blank=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit = models.CharField(max_length=20)
    received = models.DecimalField(max_digits=12, decimal_places=3, default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="proc_line_positive"),
            models.CheckConstraint(condition=models.Q(received__gte=0) & models.Q(received__lte=models.F("quantity")), name="proc_line_received"),
        ]


class PurchaseRequestHistory(models.Model):
    request = models.ForeignKey(PurchaseRequest, on_delete=models.PROTECT, related_name="history")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)
    revision = models.PositiveIntegerField()
    action = models.CharField(max_length=40)
    reason = models.CharField(max_length=1000, blank=True)
    snapshot = models.JSONField(default=dict)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["request", "revision"], name="proc_history_revision")]

import uuid
from django.conf import settings
from django.db import models

from apps.businesses.models import Business, TimeStampedModel


class SubscriptionPlan(TimeStampedModel):
    name = models.CharField(max_length=128)
    code = models.SlugField(max_length=64, unique=True)
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    limits_json = models.JSONField(default=dict, blank=True)
    features_json = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["monthly_price", "name"]

    def __str__(self):
        return self.name


class Subscription(TimeStampedModel):
    class Statuses(models.TextChoices):
        TRIAL = "trial", "Trial"
        ACTIVE = "active", "Active"
        OVERDUE = "overdue", "Overdue"
        CANCELLED = "cancelled", "Cancelled"
        PAUSED = "paused", "Paused"

    business = models.OneToOneField(Business, on_delete=models.CASCADE, related_name="subscription")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=32, choices=Statuses.choices, default=Statuses.TRIAL)
    billing_email = models.EmailField(blank=True)
    payment_method = models.CharField(max_length=64, blank=True)
    invoice_details_json = models.JSONField(default=dict, blank=True)
    requested_plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True, blank=True, related_name="requested_subscriptions")
    plan_change_requested_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    next_payment_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["business__name"]

    def __str__(self):
        return f"{self.business} - {self.plan} ({self.status})"


class UsageCounter(models.Model):
    class Metrics(models.TextChoices):
        AI_REQUESTS = "ai_requests", "AI requests"
        BOT_MESSAGES = "bot_messages", "Bot messages"
        USERS = "users", "Users"
        CONVERSATIONS = "conversations", "Conversations"

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="usage_counters")
    period_start = models.DateField()
    period_end = models.DateField()
    metric = models.CharField(max_length=32, choices=Metrics.choices)
    value = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["business", "period_start", "period_end", "metric"], name="unique_usage_counter_period_metric"),
        ]
        indexes = [
            models.Index(fields=["business", "metric", "period_start"]),
        ]

    def __str__(self):
        return f"{self.business}:{self.metric}:{self.value}"


# ADMIN-05: explicit terms are provisioned only after separate commercial approval.
# No migration seeds approved offers or enables real payment collection.
class BillingOffer(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey(Business, on_delete=models.PROTECT, related_name="billing_offers")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    expires_at = models.DateTimeField()
    approval_reference = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=False)
    # Public invoice instructions, never provider credentials or a bank statement.
    seller = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="billing_offer_positive"),
            models.CheckConstraint(condition=models.Q(period_end__gt=models.F("period_start")), name="billing_offer_period"),
        ]


class BillingOrder(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey(Business, on_delete=models.PROTECT, related_name="billing_orders")
    offer = models.OneToOneField(BillingOffer, on_delete=models.PROTECT)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    expires_at = models.DateTimeField()
    terms = models.JSONField(default=dict)
    buyer = models.JSONField(default=dict)
    subscription_revision = models.CharField(max_length=64)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    application_status = models.CharField(max_length=24, default="awaiting")
    application_code = models.CharField(max_length=48, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="billing_order_positive"),
            models.CheckConstraint(condition=models.Q(period_end__gt=models.F("period_start")), name="billing_order_period"),
        ]


class BillingAttempt(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(BillingOrder, on_delete=models.PROTECT, related_name="attempts")
    provider = models.CharField(max_length=64)
    merchant = models.CharField(max_length=128)
    status = models.CharField(max_length=24, default="creating")
    checkout_url = models.URLField(max_length=2048, blank=True)
    external_id = models.CharField(max_length=128, blank=True)
    failure_code = models.CharField(max_length=48, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["order"], condition=models.Q(status__in=["creating", "pending", "unknown"]), name="billing_one_open_attempt")]


class BillingReceipt(TimeStampedModel):
    order = models.ForeignKey(BillingOrder, on_delete=models.PROTECT, related_name="receipts")
    source = models.CharField(max_length=64)
    merchant = models.CharField(max_length=128)
    reference = models.CharField(max_length=128)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    status = models.CharField(max_length=24, default="confirmed")
    received_at = models.DateTimeField()
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    support_case = models.ForeignKey("support.SupportCase", null=True, on_delete=models.PROTECT)
    reason = models.CharField(max_length=2000, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["source", "merchant", "reference"], name="billing_unique_receipt"),
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="billing_receipt_positive"),
        ]


class BillingEvent(models.Model):
    reason = models.CharField(max_length=2000, blank=True)
    order = models.ForeignKey(BillingOrder, on_delete=models.PROTECT, related_name="events")
    kind = models.CharField(max_length=48)
    code = models.CharField(max_length=48, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    support_case = models.ForeignKey("support.SupportCase", null=True, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]

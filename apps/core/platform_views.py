from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Q, Sum
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.accounts.mfa import validate_step_up_token
from apps.ai_core.models import AIRequestLog
from apps.billing.models import Subscription
from apps.billing.usage import usage_summary
from apps.bots.models import Bot, BotChannel, BotConversation
from apps.businesses.activation import activate_landing_business
from apps.businesses.models import Business
from apps.businesses.serializers import ActivateLandingBusinessSerializer
from apps.core.audit import write_audit_log
from apps.core.models import AuditLog
from apps.core.operations_health import platform_operations_health
from apps.core.platform_reads import read_platform_source
from apps.core.service_status import platform_service_status, service_businesses, filter_service_businesses
from apps.core.platform_overview import overview_attention
from apps.core.permissions import IsPlatformAdmin, IsPlatformUser, can_log_support_action
from apps.integrations.sanitization import sanitize_error_text


from apps.core.platform_selectors import (
    _merchant_counts, _merchant_counts_many, _merchant_health,
    _merchant_support_workflow, _platform_operations_summary, platform_failure_summary,
    platform_clinic_service_statuses,
)
from apps.core.platform_serializers import PlatformMerchantFilters, PlatformSupportNoteSerializer
from rest_framework.pagination import PageNumberPagination


@api_view(["GET"])
@permission_classes([IsPlatformUser])
def platform_overview(request):
    since = timezone.now() - timedelta(days=30)
    active_subscriptions = Subscription.objects.filter(status=Subscription.Statuses.ACTIVE)
    mrr = read_platform_source(lambda: active_subscriptions.aggregate(total=Sum("plan__monthly_price"))["total"] or 0)

    return Response(
        {
            "total_businesses": Business.objects.count(),
            "active_businesses": Business.objects.filter(status=Business.Statuses.ACTIVE).count(),
            "trial_businesses": Business.objects.filter(status=Business.Statuses.TRIAL).count(),
            "generated_at": timezone.now(),
            "attention": overview_attention(request.user),
            "active_subscriptions": read_platform_source(active_subscriptions.count),
            "mrr_estimate": str(mrr) if mrr is not None else None,
            "total_users": get_user_model().objects.count(),
            "bot_count": read_platform_source(Bot.objects.count),
            "active_bot_channels": read_platform_source(lambda: BotChannel.objects.filter(status=BotChannel.Statuses.ACTIVE).count()),
            "ai_requests_30d": read_platform_source(lambda: AIRequestLog.objects.filter(created_at__gte=since).count()),
            "conversations_30d": read_platform_source(lambda: BotConversation.objects.filter(created_at__gte=since).count()),
            "operations_summary": _platform_operations_summary(since),
            "errors": platform_failure_summary(),
            "service_status": read_platform_source(platform_service_status, unavailable={
                "scope": "background_processing", "status": "unknown", "businesses": None,
            }),
        }
    )


@api_view(["GET"])
@permission_classes([IsPlatformUser])
def platform_operations_health_view(request):
    return Response(platform_operations_health())


@api_view(["GET"])
@permission_classes([IsPlatformUser])
def platform_merchants(request):
    filters = PlatformMerchantFilters(data=request.query_params)
    filters.is_valid(raise_exception=True)
    params = filters.validated_data
    businesses = (
        Business.objects.select_related("owner", "subscription", "subscription__plan")
        .order_by("-created_at", "-pk")
    )
    if params.get("search"):
        needle = params["search"]
        businesses = businesses.filter(Q(name__icontains=needle) | Q(owner__email__icontains=needle)
                                      | Q(owner__full_name__icontains=needle) | Q(slug__icontains=needle))
    if params.get("status"):
        businesses = businesses.filter(status=params["status"])
    if params.get("service"):
        businesses = filter_service_businesses(service_businesses(businesses), params["service"])
    paginator = PageNumberPagination()
    paginator.page_size = params["page_size"]
    page = paginator.paginate_queryset(businesses, request)
    counts_by_id = _merchant_counts_many(page)
    services_by_id = platform_clinic_service_statuses(page)
    data = []

    for business in page:
        subscription = getattr(business, "subscription", None)
        plan = subscription.plan if subscription else None
        counts = counts_by_id[business.pk]
        health = _merchant_health(business, counts, subscription=subscription)
        data.append(
            {
                "id": business.id,
                "name": business.name,
                "status": business.status,
                "created_at": business.created_at,
                "owner": {
                    "id": business.owner_id,
                    "email": business.owner.email,
                    "full_name": business.owner.full_name,
                },
                "plan": {
                    "id": plan.id,
                    "name": plan.name,
                    "code": plan.code,
                    "monthly_price": str(plan.monthly_price),
                }
                if plan
                else None,
                "subscription_status": subscription.status if subscription else None,
                "usage_summary": usage_summary(business),
                "operations": counts,
                "health": health,
                "service_status": services_by_id[business.pk],
                "generated_at": timezone.now(),
                "support_workflow": _merchant_support_workflow(business, counts, health),
                "latest_activity_at": counts["latest_activity_at"],
            }
        )

    return paginator.get_paginated_response(data)


@api_view(["GET"])
@permission_classes([IsPlatformUser])
def platform_merchant_detail(request, business_id):
    try:
        business = Business.objects.select_related("owner", "subscription", "subscription__plan").get(id=business_id)
    except Business.DoesNotExist:
        return Response({"detail": "Merchant not found."}, status=404)

    subscription = getattr(business, "subscription", None)
    counts = _merchant_counts(business)
    health = _merchant_health(business, counts, subscription=subscription)
    return Response(
        {
            "id": business.id,
            "name": business.name,
            "status": business.status,
            "landing_id": business.landing_id,
            "landing_domain": business.landing_domain,
            "owner": {
                "id": business.owner_id,
                "email": business.owner.email if business.owner else "",
                "full_name": business.owner.full_name if business.owner else "",
            },
            "operations": counts,
            "health": health,
            "service_status": platform_clinic_service_statuses([business])[business.pk],
            "generated_at": timezone.now(),
            "latest_activity_at": counts["latest_activity_at"],
            "created_at": business.created_at,
            "support_workflow": _merchant_support_workflow(business, counts, health),
            "can_log_support_action": can_log_support_action(request.user, business),
        }
    )


@api_view(["GET", "POST"])
@permission_classes([IsPlatformUser])
def platform_merchant_support_action(request, business_id):
    if request.method == "GET":
        if not Business.objects.filter(pk=business_id).exists():
            return Response({"detail": "Merchant not found."}, status=404)
        filters = PlatformMerchantFilters(data=request.query_params)
        filters.is_valid(raise_exception=True)
        paginator = PageNumberPagination()
        paginator.page_size = filters.validated_data["page_size"]
        logs = AuditLog.objects.filter(business_id=business_id, entity_type="platform_support_action").select_related("actor").order_by("-created_at", "-pk")
        page = paginator.paginate_queryset(logs, request)
        return paginator.get_paginated_response([
            {"id": log.pk, "business_id": business_id,
             "action_type": log.metadata.get("action_type", "support_note"),
             "note": sanitize_error_text(log.metadata.get("note", "")),
             "status": log.metadata.get("status", "logged"), "created_at": log.created_at,
             "actor_email": log.actor.email if log.actor else None}
            for log in page
        ])
    if not IsPlatformAdmin().has_permission(request, None):
        return Response({"detail": "Platform administrator access is required."}, status=403)
    validate_step_up_token(request.user, request.headers.get("X-Zani-MFA-Step-Up", ""))
    try:
        business = Business.objects.get(id=business_id)
    except Business.DoesNotExist:
        return Response({"detail": "Merchant not found."}, status=404)

    if not can_log_support_action(request.user, business):
        return Response({"detail": "An active support access grant is required."}, status=403)

    serializer = PlatformSupportNoteSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    action_type = serializer.validated_data["action_type"]
    note = sanitize_error_text(serializer.validated_data["note"])
    status = serializer.validated_data["status"]

    log = AuditLog.objects.create(
        business=business,
        actor=request.user,
        action=AuditLog.Actions.UPDATE,
        category=AuditLog.Categories.SYSTEM,
        risk_level=AuditLog.RiskLevels.LOW,
        entity_type="platform_support_action",
        entity_id=str(business.id),
        metadata={"action_type": action_type, "note": note, "status": status},
    )
    return Response(
        {
            "id": log.id,
            "business_id": business.id,
            "action_type": action_type,
            "note": note,
            "status": status,
            "created_at": log.created_at,
            "actor_email": request.user.email,
        },
        status=201,
    )


@api_view(["POST"])
@permission_classes([IsPlatformAdmin])
def platform_activate_landing(request):
    validate_step_up_token(request.user, request.headers.get("X-Zani-MFA-Step-Up", ""))
    serializer = ActivateLandingBusinessSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    result = activate_landing_business(
        landing_id=serializer.validated_data["landing_id"],
        owner_email=serializer.validated_data["owner_email"],
        owner_password=serializer.validated_data.get("owner_password") or None,
        owner_full_name=serializer.validated_data.get("owner_full_name", ""),
        business_name=serializer.validated_data["business_name"],
        business_type=serializer.validated_data.get("business_type", Business.BusinessTypes.OTHER),
        landing_domain=serializer.validated_data.get("landing_domain", ""),
        landing_preview_url=serializer.validated_data.get("landing_preview_url", ""),
        city=serializer.validated_data.get("city", ""),
        phone=serializer.validated_data.get("phone", ""),
    )
    write_audit_log(
        request,
        AuditLog.Actions.CREATE if result.created_business else AuditLog.Actions.UPDATE,
        result.business,
        business=result.business,
        metadata={
            "category": AuditLog.Categories.SECURITY,
            "risk_level": AuditLog.RiskLevels.CRITICAL,
            "kind": "platform_activation",
            "landing_id": result.business.landing_id,
            "created_business": result.created_business,
            "created_owner": result.created_owner,
            "owner_id": result.owner.id,
        },
    )
    return Response(
        {
            "business": {
                "id": result.business.id,
                "name": result.business.name,
                "slug": result.business.slug,
                "status": result.business.status,
                "landing_id": result.business.landing_id,
                "landing_domain": result.business.landing_domain,
                "landing_preview_url": result.business.landing_preview_url,
            },
            "owner": {
                "id": result.owner.id,
                "email": result.owner.email,
                "full_name": result.owner.full_name,
            },
            "subscription": {
                "id": result.subscription.id,
                "status": result.subscription.status,
                "plan": result.subscription.plan.code,
                "next_payment_at": result.subscription.next_payment_at,
            },
            "lead_form": {
                "id": result.lead_form.id,
                "public_id": result.lead_form.public_id,
                "landing_id": result.lead_form.landing_id,
            },
            "pipeline": {
                "id": result.pipeline.id,
                "name": result.pipeline.name,
                "stages_count": result.pipeline.stages.count(),
            },
            "created_owner": result.created_owner,
            "created_business": result.created_business,
        },
        status=201 if result.created_business else 200,
    )

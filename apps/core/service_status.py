"""Business-scoped background processing observations, separate from readiness.

Only current overdue work is a service signal. Historical terminal failures and
optional provider setup remain operator diagnostics, not a CRM outage.
"""
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Count, F, Min, Q
from django.utils import timezone

from apps.automations.models import AutomationRun
from apps.businesses.models import Business, BusinessMember
from apps.core.models import ExportJob, FileAttachment, ServiceComponentState
from apps.notifications.models import Notification
from apps.notifications.routing import filter_notification_recipients


COMPONENTS = tuple(ServiceComponentState.Components.values)
MONITOR_INTERVAL_SECONDS = 60
OBSERVATION_MAX_AGE_SECONDS = 180


def _notify_transition(business, row, transition):
    # Owner identity is authoritative even without an owner membership row.
    users = {member.user_id: member.user for member in BusinessMember.objects.select_related("user").filter(
        business=business, role=BusinessMember.Roles.ADMIN, is_active=True, user__is_active=True,
    )}
    if business.owner.is_active:
        users[business.owner_id] = business.owner
    recipients = filter_notification_recipients(
        business=business, users=list(users.values()), category=Notification.Categories.SYSTEM,
        priority=Notification.Priorities.NORMAL,
    )
    labels = {"automations": "Автоматизации", "notifications": "Уведомления", "exports": "Экспорт", "files": "Проверка файлов"}
    message = ("Обработка задерживается. Проверьте состояние сервиса перед повтором действий."
               if transition == "started" else
               "Задержка обработки устранена. Результат отдельных действий проверьте в их истории.")
    now = timezone.now()
    # Already delivered in-app, in the same transaction as the incident. This
    # does not depend on the worker whose delay we may be reporting.
    Notification.objects.bulk_create([
        Notification(business=business, recipient=user, channel=Notification.Channels.SYSTEM,
                     category=Notification.Categories.SYSTEM, priority=Notification.Priorities.NORMAL,
                     text=f"{labels[row.component]}: {message}", send_at=now,
                     provider_reference=f"service-status:{row.pk}:{row.episode}:{transition}",
                     status=Notification.Statuses.SENT, delivered_at=now)
        for user in recipients
    ])


def overdue_work_counts(business, *, now):
    """Bounded counts, no customer text, entity IDs or external probes."""
    automation_cutoff = now - timedelta(seconds=settings.AUTOMATION_STALE_LOCK_SECONDS)
    export_cutoff = now - timedelta(seconds=settings.EXPORT_STALE_SECONDS)
    # In-app delivery normally runs each minute; use the existing 15-minute
    # internal runtime deadline before classifying a delay as an incident.
    notification_cutoff = now - timedelta(seconds=settings.AUTOMATION_STALE_LOCK_SECONDS)
    file_cutoff = now - timedelta(seconds=settings.FILE_SCAN_LEASE_SECONDS)
    return {
        "automations": AutomationRun.objects.filter(business=business).filter(
            Q(status__in=["pending", "waiting"], run_after__lte=automation_cutoff)
            | Q(status="pending", run_after__isnull=True, created_at__lte=automation_cutoff)
            | Q(status="retry_scheduled", next_retry_at__lte=automation_cutoff)
            | Q(status="running", locked_at__lte=automation_cutoff)
            | Q(status="running", locked_at__isnull=True, created_at__lte=automation_cutoff)
        ).count(),
        "notifications": Notification.objects.filter(business=business, channel="system").filter(
            Q(status="pending", send_at__lte=notification_cutoff)
            | Q(status="retry_scheduled", next_retry_at__lte=notification_cutoff)
            | Q(status="sending", locked_at__lte=notification_cutoff)
            | Q(status="sending", locked_at__isnull=True, send_at__lte=notification_cutoff)
        ).count(),
        "exports": ExportJob.objects.filter(business=business).filter(
            Q(status="pending", created_at__lte=export_cutoff)
            | Q(status="running", started_at__lte=export_cutoff)
            | Q(status="running", started_at__isnull=True, created_at__lte=export_cutoff)
        ).count(),
        "files": FileAttachment.objects.filter(business=business).filter(
            Q(scan_status__in=["pending", "error"], created_at__lte=file_cutoff)
            | Q(scan_status="scanning", scan_started_at__lte=file_cutoff)
            | Q(scan_status="scanning", scan_started_at__isnull=True, created_at__lte=file_cutoff)
        ).count(),
    }


def _record_observation(business, component, count, observed_at):
    """Caller holds the Business row lock for both sampling and transitions."""
    row = ServiceComponentState.objects.filter(business=business, component=component).first()
    if row is not None and observed_at <= row.observed_at:
        return None
    degraded = count > 0
    previous = row.state if row else None
    if row is None:
        row = ServiceComponentState(business=business, component=component)
    transition = None
    if degraded and previous != "degraded":
        row.episode += 1
        row.started_at = observed_at
        row.recovered_at = None
        transition = "started"
    elif not degraded and previous == "degraded":
        row.recovered_at = observed_at
        transition = "recovered"
    row.state = "degraded" if degraded else "healthy"
    row.observed_at = observed_at
    row.affected_count = count
    row.save()
    return (row, transition) if transition else None


@transaction.atomic
def observe_business_service(business_id, *, now=None):
    # Lock before reading jobs: overlapping collectors cannot apply stale samples
    # or duplicate a start/recovery notification after waiting for another writer.
    business = Business.objects.select_for_update().get(pk=business_id)
    observed_at = now or timezone.now()
    counts = overdue_work_counts(business, now=observed_at)
    transitions = []
    for component in COMPONENTS:
        result = _record_observation(business, component, counts[component], observed_at)
        if result:
            transitions.append(result)
            _notify_transition(business, *result)
    return transitions


def business_service_status(business, *, now=None):
    now = now or timezone.now()
    rows = {row.component: row for row in ServiceComponentState.objects.filter(business=business)}
    return _business_service_status_from_rows(rows, now=now)


def business_service_status_many(business_ids, *, now=None):
    """Same observation contract for a platform page, with one scoped query."""
    now = now or timezone.now()
    rows_by_business = {pk: {} for pk in business_ids}
    for row in ServiceComponentState.objects.filter(business_id__in=rows_by_business):
        rows_by_business[row.business_id][row.component] = row
    return {pk: _business_service_status_from_rows(rows, now=now)
            for pk, rows in rows_by_business.items()}


def _business_service_status_from_rows(rows, *, now):
    components = []
    for component in COMPONENTS:
        row = rows.get(component)
        stale = row is None or row.observed_at < now - timedelta(seconds=OBSERVATION_MAX_AGE_SECONDS) or row.observed_at > now
        components.append({
            "component": component,
            "state": "unknown" if stale else row.state,
            "last_state": row.state if row else None,
            "observed_at": row.observed_at if row else None,
            "started_at": row.started_at if row else None,
            "recovered_at": row.recovered_at if row else None,
            "episode": row.episode if row else 0,
        })
    states = {item["state"] for item in components}
    return {
        "status": "degraded" if "degraded" in states else "unknown" if "unknown" in states else "healthy",
        "checked_at": now,
        "max_age_seconds": OBSERVATION_MAX_AGE_SECONDS,
        "components": components,
    }


def observe_service_batch(*, limit=100):
    # Oldest-first rotation also reaches never-observed businesses; no permanent
    # first-page cap. A stopped collector naturally makes observations stale.
    business_ids = list(Business.objects.annotate(
        last_observed=Min("service_component_states__observed_at"),
    ).order_by(F("last_observed").asc(nulls_first=True), "pk").values_list("pk", flat=True)[:max(1, min(limit, 1000))])
    for business_id in business_ids:
        observe_business_service(business_id)
    return len(business_ids)


def service_businesses(queryset=None, *, now=None):
    """Shared distinct-clinic classification for overview counts and filtered lists."""
    now = now or timezone.now()
    fresh = Q(service_component_states__observed_at__gte=now - timedelta(seconds=OBSERVATION_MAX_AGE_SECONDS),
              service_component_states__observed_at__lte=now)
    return (Business.objects.all() if queryset is None else queryset).annotate(
        fresh_count=Count("service_component_states", filter=fresh),
        degraded_count=Count("service_component_states", filter=fresh & Q(service_component_states__state="degraded")),
    )


def filter_service_businesses(queryset, status):
    if status == "degraded":
        return queryset.filter(degraded_count__gt=0)
    if status == "healthy":
        return queryset.filter(fresh_count=len(COMPONENTS), degraded_count=0)
    if status == "unknown":
        return queryset.filter(fresh_count__lt=len(COMPONENTS), degraded_count=0)
    return queryset.filter(Q(degraded_count__gt=0) | Q(fresh_count__lt=len(COMPONENTS)))


def platform_service_status(*, now=None):
    now = now or timezone.now()
    businesses = service_businesses(now=now)
    total = businesses.count()
    degraded = businesses.filter(degraded_count__gt=0).count()
    healthy = businesses.filter(fresh_count=len(COMPONENTS), degraded_count=0).count()
    return {
        "scope": "background_processing", "checked_at": now,
        "status": "degraded" if degraded else "unknown" if not total or total > healthy else "healthy",
        "businesses": {"total": total, "healthy": healthy, "degraded": degraded, "unknown": total - healthy - degraded},
        "monitor_interval_seconds": MONITOR_INTERVAL_SECONDS,
        "max_age_seconds": OBSERVATION_MAX_AGE_SECONDS,
        "incidents": list(ServiceComponentState.objects.filter(
            state="degraded", observed_at__gte=now - timedelta(seconds=OBSERVATION_MAX_AGE_SECONDS), observed_at__lte=now,
        ).order_by("started_at", "pk").values("business_id", "component", "episode", "started_at", "observed_at", "affected_count")[:10]),
    }

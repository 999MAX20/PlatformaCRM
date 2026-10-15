"""Add idempotent synthetic diagnostics to the explicitly authorized local stand.

Run via Django shell only after preparing output/platform-admin-demo-20261015.
This fixture creates records, never dispatches jobs or contacts providers.
"""
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.automations.models import AutomationRun
from apps.businesses.models import Business
from apps.core.models import ServiceComponentState
from apps.integrations.models import BusinessConnector, IntegrationEventLog, WebhookDeliveryLog, WebhookEndpoint
from apps.support.incidents import link_incident
from apps.support.services import create_case


def seed():
    folder = Path(settings.BASE_DIR) / "output" / "platform-admin-demo-20261015"
    database = settings.DATABASES["default"]
    if (database["ENGINE"] != "django.db.backends.sqlite3"
            or Path(database["NAME"]).resolve() != (folder / "db.sqlite3").resolve()
            or not (folder / "seeded.json").is_file()):
        raise RuntimeError("Diagnostics fixtures require the prepared, isolated local demo database.")
    with transaction.atomic():
        return _seed()


def _seed():
    now = timezone.now()
    business = Business.objects.get(slug="overview-browser-0")
    staff = User.objects.get(email="platform_admin@example.com")
    # Preserve the existing ERROR record and any manual changes made to it.
    for status, name in (
        ("failed", "ДЕМО — Неудачная синхронизация"),
        ("expired_credentials", "ДЕМО — Истёк доступ к источнику"),
        ("needs_attention", "ДЕМО — Требуется настройка"),
        ("disabled", "ДЕМО — Отключённый источник"),
    ):
        BusinessConnector.objects.get_or_create(
            business=business, provider="website", name=name,
            defaults={"status": status, "last_error": "" if status in ("disabled", "needs_attention") else "Демонстрационный диагностический пример"},
        )
    for status in ("failed", "processed"):
        IntegrationEventLog.objects.get_or_create(
            business=business, provider="website", channel="demo-diagnostics", direction="inbound", status=status,
            defaults={"error": "Демо: входящие данные отклонены" if status == "failed" else ""},
        )
    endpoint, _ = WebhookEndpoint.objects.get_or_create(
        business=business, name="ДЕМО — История доставки (отключено)",
        defaults={"url": "http://127.0.0.1:9/demo-disabled", "is_active": False, "created_by": staff},
    )
    for status in ("failed", "sent"):
        WebhookDeliveryLog.objects.get_or_create(
            business=business, endpoint=endpoint, idempotency_key=f"demo-diagnostics-{status}",
            defaults={"event_type": "lead.created", "status": status, "attempts": 3 if status == "failed" else 1,
                      "response_status": 503 if status == "failed" else 200,
                      "error": "Демо: доставка завершилась ошибкой" if status == "failed" else "",
                      "delivered_at": now if status == "sent" else None},
        )
    for status in ("failed", "success"):
        AutomationRun.objects.get_or_create(
            business=business, idempotency_key=f"demo-diagnostics-{status}",
            defaults={"trigger_type": "manual", "status": status, "attempts": 3 if status == "failed" else 1,
                      "started_at": now-timezone.timedelta(minutes=20), "finished_at": now,
                      "error": "Демо: автоматизация завершилась ошибкой" if status == "failed" else ""},
        )
    scenarios = {}
    for scenario, name in (("stale", "ДЕМО — Устаревшая проверка"), ("recovered", "ДЕМО — Сервис восстановлен")):
        target, _ = Business.objects.get_or_create(
            slug=f"demo-diagnostics-{scenario}",
            defaults={"owner": business.owner, "name": name, "status": "active", "timezone": "Asia/Almaty"},
        )
        for component in ServiceComponentState.Components.values:
            ServiceComponentState.objects.get_or_create(
                business=target, component=component,
                defaults={"state": "degraded" if component == "exports" else "healthy",
                          "observed_at": now, "episode": 1 if component == "exports" else 0,
                          "started_at": now-timezone.timedelta(hours=2) if component == "exports" else None,
                          "affected_count": 2 if component == "exports" else 0},
            )
        case_result = create_case(
            actor=staff, business_id=target.pk,
            subject="Демо: проверка устарела" if scenario == "stale" else "Демо: восстановление выгрузки подтверждено",
            text="Синтетический пример для просмотра диагностики и связанного обращения.",
            idempotency_key=f"demo-diagnostics-{scenario}", platform=True,
        )
        case_id = case_result.data["case_id"]
        link_incident(actor=staff, case_id=case_id, business_id=target.pk, component="exports", episode=1)
        if scenario == "stale":
            # Supervisor explicitly excludes this fixture from timestamp refresh.
            ServiceComponentState.objects.filter(business=target).update(observed_at=now-timezone.timedelta(minutes=15))
        else:
            ServiceComponentState.objects.filter(business=target, component="exports").update(
                state="healthy", affected_count=0, recovered_at=now-timezone.timedelta(minutes=5), observed_at=now,
            )
        scenarios[scenario] = {"business": target.pk, "case": case_id}
    return {"connectors_business": business.pk, **scenarios}

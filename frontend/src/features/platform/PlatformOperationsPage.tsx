import { PlatformLoadError } from "./PlatformData";
import { valueOrUnknown } from "./PlatformData";
import { Button } from "../../components/ui/Button";
import { StatusNotice } from "../../components/ui/StatusNotice";
import { PageHeader } from "../../components/ui/PageHeader";
import { useQuery } from "@tanstack/react-query";
import { Activity, AlertTriangle, CheckCircle2, CircleDot, PlugZap, ServerCog, ShieldCheck, Workflow } from "lucide-react";
import { Link } from "react-router";

import { asArray } from "../../api/client";
import { platformApi } from "../../api/platform";
import { Card, CardBody } from "../../components/ui/Card";
import { LoadingState } from "../../components/ui/StateViews";
import { cn } from "../../lib/cn";
import { useI18n } from "../../lib/i18n";

function statusTone(status: string) {
  if (["healthy", "ready", "pass"].includes(status)) return "bg-[var(--platforma-success-soft)] text-platforma-success border-platforma-success/20";
  if (["warning", "warn"].includes(status)) return "bg-[var(--platforma-warning-soft)] text-platforma-warning border-platforma-warning/20";
  return "bg-[var(--platforma-danger-soft)] text-platforma-danger border-platforma-danger/20";
}

function StatusPill({ status }: { status: string }) {
  return <span className={cn("rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.12em]", statusTone(status))}>{status}</span>;
}

function EmptyLine({ label }: { label: string }) {
  return <p className="rounded-control border border-dashed border-platforma-border bg-surface-muted px-4 py-3 text-sm font-semibold text-platforma-faint">{label}</p>;
}

export function PlatformOperationsPage() {
  const { t } = useI18n();
  const health = useQuery({ queryKey: ["platform-operations-health"], queryFn: platformApi.operationsHealth });

  if (health.isLoading) return <LoadingState scope="page" />;
  if (health.isError || !health.data) return <PlatformLoadError error={health.error} message={t("platform.operations.error")} onRetry={() => health.refetch()} />;

  const data = health.data;
  const productionFailedItems = asArray<typeof data.runtime.production_readiness.failed_items[number]>(data.runtime.production_readiness.failed_items);
  const backupFailedItems = asArray<typeof data.runtime.backup_readiness.failed_items[number]>(data.runtime.backup_readiness.failed_items);
  const providerRolloutItems = asArray<typeof data.runtime.provider_rollout.providers[number]>(data.runtime.provider_rollout.providers);
  const queueNames = asArray<string>(data.runtime.queue.queues);
  const connectorRequests = asArray<typeof data.work_queue.connector_requests[number]>(data.work_queue.connector_requests);
  const failedAutomationRuns = asArray<typeof data.work_queue.failed_automation_runs[number]>(data.work_queue.failed_automation_runs);
  const failedIntegrationEvents = asArray<typeof data.work_queue.failed_integration_events[number]>(data.work_queue.failed_integration_events);
  const failedItems = [
    ...productionFailedItems,
    ...backupFailedItems,
  ].slice(0, 8);

  return (
    <div className="space-y-5">
      <PageHeader title={t("platform.operations.title")} actions={<Button variant="secondary" onClick={() => health.refetch()} isLoading={health.isFetching}>{t("platform.merchantDetail.refresh")}</Button>} />

      {!!data.unavailable_sources?.length && <StatusNotice compact tone="warning" title={t("platform.workspace.partial")} />}
      <StatusNotice data-testid="platform-service-state" compact role="status" ariaLive="polite"
        tone={data.service_status?.status === "degraded" ? "warning" : data.service_status?.status === "healthy" ? "success" : "info"}
        title={t(`serviceStatus.platform.${data.service_status?.status || "unknown"}`)}
        description={data.service_status?.businesses ? t("serviceStatus.platform.counts", data.service_status.businesses) : t("serviceStatus.unknown.text")} />
      {!!data.service_status?.incidents?.length && <Card><CardBody className="space-y-2 p-4">
        {data.service_status.incidents.map(item => <Link key={`${item.business_id}:${item.component}:${item.episode}`} to={`/platform/merchants/${item.business_id}`} className="platforma-focus-ring block rounded-control border border-platforma-border p-3 text-sm">
          {t("platform.merchants.merchant")} #{item.business_id} · {t(`serviceStatus.component.${item.component}`)} · {t("serviceStatus.platform.overdue", { count: item.affected_count })}
        </Link>)}
      </CardBody></Card>}
      <div className="flex flex-wrap items-center justify-between gap-2"><h2 className="text-lg font-semibold">{t("serviceStatus.platform.diagnostics")}</h2><StatusPill status={data.status} /></div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardBody className="p-5">
            <AlertTriangle className="text-platforma-danger" size={22} />
            <p className="mt-2 text-2xl font-semibold text-platforma-text">{data.summary.critical}</p>
            <p className="text-sm font-semibold text-platforma-faint">{t("platform.operations.critical")}</p>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="p-5">
            <CircleDot className="text-platforma-warning" size={22} />
            <p className="mt-2 text-2xl font-semibold text-platforma-text">{data.summary.warning}</p>
            <p className="text-sm font-semibold text-platforma-faint">{t("platform.operations.warnings")}</p>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="p-5">
            <ShieldCheck className="text-brand-600" size={22} />
            <p className="mt-2 text-2xl font-semibold text-platforma-text">{valueOrUnknown(data.summary.active_support_grants)}</p>
            <p className="text-sm font-semibold text-platforma-faint">{t("platform.operations.supportGrants")}</p>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="p-5">
            <PlugZap className="text-platforma-info" size={22} />
            <p className="mt-2 text-2xl font-semibold text-platforma-text">{valueOrUnknown(data.summary.connector_requests)}</p>
            <p className="text-sm font-semibold text-platforma-faint">{t("platform.operations.connectorWorkItems")}</p>
          </CardBody>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <Card>
          <CardBody className="p-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold text-platforma-text">{t("platform.operations.queueRuntime")}</h2>
                <p className="mt-1 text-sm text-platforma-faint">{t("platform.operations.queueRuntimeText")}</p>
              </div>
              <StatusPill status={data.runtime.queue.status} />
            </div>
            <div className="mt-5 grid gap-3 sm:grid-cols-3">
              <div className="rounded-card border border-platforma-border bg-surface-muted p-4">
                <ServerCog size={20} className="text-brand-600" />
                <p className="mt-3 text-2xl font-semibold text-platforma-text">{valueOrUnknown(data.runtime.queue.automation_runs.pending)}</p>
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-platforma-faint">{t("platform.operations.pending")}</p>
              </div>
              <div className="rounded-card border border-platforma-border bg-surface-muted p-4">
                <Workflow size={20} className="text-platforma-warning" />
                <p className="mt-3 text-2xl font-semibold text-platforma-text">{valueOrUnknown(data.runtime.queue.automation_runs.running)}</p>
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-platforma-faint">{t("platform.operations.running")}</p>
              </div>
              <div className="rounded-card border border-platforma-border bg-surface-muted p-4">
                <AlertTriangle size={20} className="text-platforma-danger" />
                <p className="mt-3 text-2xl font-semibold text-platforma-text">{valueOrUnknown(data.runtime.queue.automation_runs.failed)}</p>
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-platforma-faint">{t("platform.operations.failed")}</p>
              </div>
            </div>
            <p className="mt-4 text-sm leading-6 text-platforma-faint">
              {t("platform.operations.broker", {
                broker: data.runtime.queue.broker_configured ? t("platform.operations.configured") : t("platform.operations.notConfigured"),
                inline: String(data.runtime.queue.automation_inline),
                queues: queueNames.join(", ") || t("platform.operations.none"),
              })}
            </p>
          </CardBody>
        </Card>

        <Card>
          <CardBody className="p-4">
            <h2 className="text-xl font-semibold text-platforma-text">{t("platform.operations.productionGates")}</h2>
            <p className="mt-1 text-sm text-platforma-faint">{t("platform.operations.productionGatesText")}</p>
            <div className="mt-5 space-y-3">
              {failedItems.length ? failedItems.map((item) => (
                <div key={item.key} className="rounded-card border border-platforma-danger/20 bg-platforma-dangerSoft/60 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-semibold text-platforma-danger">{item.title || item.key}</p>
                    <StatusPill status={item.status} />
                  </div>
                  <p className="mt-2 text-sm text-platforma-danger">{item.detail}</p>
                  <p className="mt-2 text-xs font-semibold text-platforma-danger">{item.action}</p>
                </div>
              )) : <EmptyLine label={t("platform.operations.noProductionBlockers")} />}
            </div>
          </CardBody>
        </Card>
      </div>

      <Card>
        <CardBody className="p-4">
          <h2 className="text-xl font-semibold text-platforma-text">{t("platform.operations.providerRollout")}</h2>
          <p className="mt-1 text-sm text-platforma-faint">{t("platform.operations.providerRolloutText")}</p>
          <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {providerRolloutItems.map((provider) => (
              <div key={provider.provider} className="rounded-card border border-platforma-border bg-surface-card p-4 shadow-xs">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-platforma-faint">#{provider.order} {provider.provider}</p>
                    <h3 className="mt-1 font-semibold text-platforma-text">{provider.title}</h3>
                  </div>
                  <StatusPill status={provider.status} />
                </div>
                <p className="mt-3 text-sm text-platforma-faint">{t("platform.operations.enabled", { value: String(provider.enabled) })}</p>
              </div>
            ))}
          </div>
        </CardBody>
      </Card>

      <p className="rounded-control border border-platforma-border bg-surface-card p-3 text-sm text-platforma-subtle">{t("platform.support.recoveryByClinic")}</p>
      <div className="grid gap-4 xl:grid-cols-3">
        <Card>
          <CardBody className="p-4">
            <h2 className="text-lg font-semibold text-platforma-text">{t("platform.operations.connectorQueue")}</h2>
            <div className="mt-4 space-y-3">
              {connectorRequests.length ? connectorRequests.map((item) => (
                <Link key={item.id} to={`/platform/merchants/${item.business_id}`} className="block rounded-card border border-platforma-border bg-surface-muted p-4 transition hover:border-brand-200 hover:bg-surface-card">
                  <p className="font-semibold text-platforma-text">{item.business_name || `${t("platform.merchants.merchant")} #${item.business_id}`}</p>
                  <p className="mt-1 text-sm text-platforma-faint">{item.provider} · {item.status}</p>
                  {["failed", "expired_credentials"].includes(item.status) && <p className="mt-2 text-xs font-semibold text-platforma-danger">{t("platform.operations.failureRecorded")}</p>}
                </Link>
              )) : <EmptyLine label={t(data.unavailable_sources?.includes("connector_requests") ? "platform.workspace.unknown" : "platform.operations.noConnectorRequests")} />}
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody className="p-4">
            <h2 className="text-lg font-semibold text-platforma-text">{t("platform.operations.automationFailures")}</h2>
            <div className="mt-4 space-y-3">
              {failedAutomationRuns.length ? failedAutomationRuns.map((item) => (
                <Link key={item.id} to={`/platform/merchants/${item.business_id}`} className="block rounded-card border border-platforma-border bg-surface-muted p-4 transition hover:border-brand-200 hover:bg-surface-card">
                  <p className="font-semibold text-platforma-text">{item.business_name || `${t("platform.merchants.merchant")} #${item.business_id}`}</p>
                  <p className="mt-1 text-sm text-platforma-faint">{item.trigger_type} · {t("platform.operations.attempts", { attempts: item.attempts, max: item.max_attempts })}</p>
                  <p className="mt-2 text-xs font-semibold text-platforma-danger">{t("platform.operations.failureRecorded")}</p>
                </Link>
              )) : <EmptyLine label={t(data.unavailable_sources?.includes("failed_automation_runs") ? "platform.workspace.unknown" : "platform.operations.noFailedAutomationRuns")} />}
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody className="p-4">
            <h2 className="text-lg font-semibold text-platforma-text">{t("platform.operations.integrationFailures")}</h2>
            <div className="mt-4 space-y-3">
              {failedIntegrationEvents.length ? failedIntegrationEvents.map((item) => (
                <Link key={item.id} to={item.business_id ? `/platform/merchants/${item.business_id}` : "/platform/operations"} className="block rounded-card border border-platforma-border bg-surface-muted p-4 transition hover:border-brand-200 hover:bg-surface-card">
                  <p className="font-semibold text-platforma-text">{item.business_name || (item.business_id ? `${t("platform.merchants.merchant")} #${item.business_id}` : t("platform.operations.noBusiness"))}</p>
                  <p className="mt-1 text-sm text-platforma-faint">{item.provider} · {item.direction}</p>
                  <p className="mt-2 text-xs font-semibold text-platforma-danger">{t("platform.operations.failureRecorded")}</p>
                </Link>
              )) : <EmptyLine label={t(data.unavailable_sources?.includes("failed_integration_events") ? "platform.workspace.unknown" : "platform.operations.noFailedIntegrationEvents")} />}
            </div>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}

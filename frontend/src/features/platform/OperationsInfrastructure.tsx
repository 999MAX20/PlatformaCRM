import { useQuery } from "@tanstack/react-query";
import { platformApi } from "../../api/platform";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { LoadingState } from "../../components/ui/StateViews";
import { StatusNotice } from "../../components/ui/StatusNotice";
import { useI18n } from "../../lib/i18n";
import type { PlatformHealthGate } from "../../types";
import { PlatformLoadError, platformDate, valueOrUnknown } from "./PlatformData";

function GateList({ title, items }: { title: string; items: PlatformHealthGate[] }) {
  const { t } = useI18n();
  return <Card padding="md" className="space-y-3"><h2 className="font-semibold">{title}</h2>
    {items.length ? <ul className="divide-y divide-platforma-border">{items.map(item => <li key={item.key} className="space-y-2 py-3 text-sm">
      <p className="font-medium">{item.title || item.key} · <span className="text-platforma-warning">{t(`operationsWorkspace.status.${item.status}`)}</span></p>
      <p className="break-words text-platforma-subtle">{item.detail}</p><p className="break-words text-xs text-platforma-subtle">{item.action}</p>
    </li>)}</ul> : <p className="text-sm text-platforma-subtle">{t("platform.operations.noProductionBlockers")}</p>}
  </Card>;
}

export function OperationsInfrastructure() {
  const { t, language } = useI18n();
  const health = useQuery({ queryKey: ["platform-operations-health"], queryFn: platformApi.operationsHealth, refetchInterval: 30_000 });
  if (health.isPending) return <LoadingState scope="page" />;
  if (health.isError || !health.data) return <PlatformLoadError error={health.error} message={t("platform.operations.error")} onRetry={() => health.refetch()} />;
  const data = health.data, queue = data.runtime.queue;
  const metrics: Array<[string, number | null]> = [["platform.operations.pending", queue.automation_runs.pending], ["platform.operations.running", queue.automation_runs.running], ["operationsWorkspace.failedTotal", queue.automation_runs.failed], ["platform.operations.supportGrants", data.summary.active_support_grants]];
  return <div className="space-y-4" data-testid="operations-infrastructure">
    <div className="flex flex-wrap items-center justify-between gap-2"><h2 className="text-base font-semibold">{t("serviceStatus.platform.diagnostics")}</h2><Button variant="secondary" isLoading={health.isFetching} onClick={() => health.refetch()}>{t("common.refresh")}</Button></div>
    <p className="text-xs text-platforma-subtle">{data.environment} · {data.release} · {t("operationsWorkspace.updated", { time: platformDate(data.generated_at, language) })}</p>
    {!!data.unavailable_sources?.length && <StatusNotice compact tone="warning" title={t("platform.workspace.partial")} />}
    <Card padding="md" className="space-y-3"><h2 className="font-semibold">{t("platform.operations.queueRuntime")}</h2>
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">{metrics.map(([key, value]) => <div key={key}><dt className="text-xs text-platforma-subtle">{t(key)}</dt><dd className="mt-1 text-xl font-semibold tabular-nums">{valueOrUnknown(value)}</dd></div>)}</dl>
      <p className="text-xs text-platforma-subtle">{t("platform.operations.broker", { broker: queue.broker_configured ? t("platform.operations.configured") : t("platform.operations.notConfigured"), inline: String(queue.automation_inline), queues: queue.queues.join(", ") || t("platform.operations.none") })}</p>
    </Card>
    <div className="grid items-start gap-4 xl:grid-cols-2">
      <GateList title={t("operationsWorkspace.production")} items={[...data.runtime.production_readiness.failed_items, ...data.runtime.production_readiness.warning_items]} />
      <GateList title={t("operationsWorkspace.backups")} items={data.runtime.backup_readiness.failed_items} />
    </div>
    <Card padding="md" className="space-y-3"><h2 className="font-semibold">{t("platform.operations.providerRollout")}</h2>
      <div className="divide-y divide-platforma-border">{data.runtime.provider_rollout.providers.map(provider => <details key={provider.provider} className="py-3">
        <summary className="platforma-focus-ring cursor-pointer text-sm font-medium">{provider.title} · {t(`operationsWorkspace.status.${provider.status}`)}</summary>
        <p className="my-2 text-xs text-platforma-subtle">{t("platform.operations.enabled", { value: String(provider.enabled) })}</p>
        <ul className="space-y-2 text-sm">{provider.gates.map(item => <li key={item.key} className="break-words"><span className="font-medium">{item.title || item.key}</span> · {t(`operationsWorkspace.status.${item.status}`)}<p className="text-xs text-platforma-subtle">{item.detail} {item.action}</p></li>)}</ul>
      </details>)}</div>
    </Card>
  </div>;
}

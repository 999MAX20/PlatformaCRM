import { PlatformLoadError } from "./PlatformData";
import { useQuery } from "@tanstack/react-query";
import { Link, useLocation, useSearchParams } from "react-router";
import { platformApi } from "../../api/platform";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { PageHeader } from "../../components/ui/PageHeader";
import { CrmPagination } from "../../components/crm/CrmPagination";
import { LoadingState, EmptyState } from "../../components/ui/StateViews";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";
import { useI18n } from "../../lib/i18n";
import { PlatformServiceBadge, platformDate, valueOrUnknown } from "./PlatformData";

export function PlatformMerchantsPage() {
  const { t, language } = useI18n();
  const location = useLocation();
  const [params, setParams] = useSearchParams();
  const query = params.get("search") || "";
  const status = params.get("status") || "";
  const page = Math.max(1, Math.floor(Number(params.get("page")) || 1));
  const pageSize = [10, 20, 30, 50, 100].includes(Number(params.get("page_size"))) ? Number(params.get("page_size")) : 20;
  const search = useDebouncedValue(query, 250);
  const merchants = useQuery({ queryKey: ["platform-merchants", search, status, page, pageSize], queryFn: () => platformApi.merchants({ search, status: status || undefined, page, page_size: pageSize }) });
  function update(values: Record<string, string>) {
    setParams(current => { const next = new URLSearchParams(current); for (const [key, value] of Object.entries(values)) { if (value) next.set(key, value); else next.delete(key); } return next; }, { replace: true });
  }
  const rows = merchants.data?.results || [];
  const filtered = Boolean(query || status);
  return <div className="space-y-4" data-testid="platform-merchants-ready">
    <PageHeader title={t("platform.merchants.title")} />
    <div className="flex flex-wrap items-center gap-2">
      <Input aria-label={t("platform.merchants.search")} placeholder={t("platform.merchants.search")} value={query} onChange={event => update({ search: event.target.value, page: "" })} className="w-full sm:w-80" />
      <Select aria-label={t("platform.merchants.status")} value={status} onChange={event => update({ status: event.target.value, page: "" })} className="w-48" options={[
        { value: "", label: t("platform.workspace.allStatuses") },
        ...["active", "trial", "inactive", "blocked"].map(value => ({ value, label: t(`platform.workspace.status.${value}`) })),
      ]} />
      {filtered && <Button variant="ghost" onClick={() => update({ search: "", status: "", page: "" })}>{t("tasks.resetFilters")}</Button>}
      <Button variant="secondary" onClick={() => merchants.refetch()} isLoading={merchants.isFetching}>{t("platform.merchantDetail.refresh")}</Button>
    </div>
    {merchants.isPending ? <LoadingState scope="page" /> : merchants.isError ? <PlatformLoadError error={merchants.error} message={t("platform.merchants.error")} onRetry={() => merchants.refetch()} /> : !rows.length ? <EmptyState title={t(filtered ? "platform.merchants.emptyTitle" : "platform.workspace.noClinics")} description={t(filtered ? "platform.workspace.noMatches" : "platform.workspace.noClinicsText")} /> : <Card>
      <table className="block w-full text-left text-sm md:table">
        <thead className="sr-only border-b border-platforma-border bg-surface-muted text-xs text-platforma-subtle md:not-sr-only md:table-header-group"><tr>
          {["platform.merchants.merchant", "platform.merchants.status", "platform.workspace.configuration", "platform.workspace.serviceTitle", "platform.workspace.lastActivity"].map(key => <th scope="col" className="px-4 py-3 font-medium" key={key}>{t(key)}</th>)}
        </tr></thead>
        <tbody className="block md:table-row-group">{rows.map(merchant => <tr key={merchant.id} className="grid grid-cols-2 gap-y-1 border-b border-platforma-border py-3 last:border-0 hover:bg-surface-hover md:table-row md:py-0" data-testid="platform-clinic-row">
          <td className="col-span-2 min-w-0 px-4 py-2 align-top md:py-4"><Link state={{ returnTo: location.pathname + location.search }} to={`/platform/merchants/${merchant.id}`} className="platforma-focus-ring break-words font-semibold text-platforma-text hover:text-brand-700">{merchant.name}</Link><p className="mt-1 break-all text-xs text-platforma-subtle">{merchant.owner.full_name || merchant.owner.email || t("platform.common.noName")}</p><p className="mt-1 text-xs text-platforma-faint">#{merchant.id}</p></td>
          <td className="min-w-0 px-4 py-2 align-top md:py-4"><p className="text-xs text-platforma-faint md:hidden">{t("platform.merchants.status")}</p><p>{t(`platform.workspace.status.${merchant.status}`)}</p><p className="mt-1 text-xs text-platforma-subtle">{merchant.plan?.name || t("platform.merchants.noPlan")} · {merchant.subscription_status ? t(`platform.workspace.subscription.${merchant.subscription_status}`) : t("platform.merchants.noSubscription")}</p></td>
          <td className="min-w-0 px-4 py-2 align-top text-xs leading-6 text-platforma-subtle md:py-4"><p className="text-platforma-faint md:hidden">{t("platform.workspace.configuration")}</p><p>{t("platform.workspace.connectedSources", { count: valueOrUnknown(merchant.operations?.connected_connectors) })}</p><p>{t("platform.workspace.pendingSources", { count: valueOrUnknown(merchant.operations?.pending_connectors) })}</p>{!!merchant.operations?.failed_connectors && <p className="text-platforma-warning">{t("platform.workspace.failedSources", { count: merchant.operations.failed_connectors })}</p>}</td>
          <td className="min-w-0 px-4 py-2 align-top md:py-4"><p className="mb-1 text-xs text-platforma-faint md:hidden">{t("platform.workspace.serviceTitle")}</p><PlatformServiceBadge service={merchant.service_status} /></td>
          <td className="min-w-0 px-4 py-2 align-top text-xs text-platforma-subtle md:py-4"><p className="mb-1 text-platforma-faint md:hidden">{t("platform.workspace.lastActivity")}</p><p>{platformDate(merchant.latest_activity_at, language)}</p><p className="mt-1">{t("platform.merchants.usageText", { ai: valueOrUnknown(merchant.usage_summary?.find(item => item.metric === "ai_requests")?.value), messages: valueOrUnknown(merchant.usage_summary?.find(item => item.metric === "bot_messages")?.value) })}</p></td>
        </tr>)}</tbody>
      </table>
      <CrmPagination compact shown={rows.length} total={merchants.data?.count || 0} page={page} pageSize={pageSize} onPageChange={value => update({ page: String(value) })} onPageSizeChange={value => update({ page_size: String(value), page: "" })} previousLabel={t("pagination.previous")} nextLabel={t("pagination.next")} />
    </Card>}
    <p className="text-xs text-platforma-faint">{t("platform.workspace.activityScope")}</p>
  </div>;
}

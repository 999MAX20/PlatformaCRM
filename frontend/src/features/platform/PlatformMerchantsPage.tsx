import { useQuery } from "@tanstack/react-query";
import { Link, useLocation, useSearchParams } from "react-router";
import { platformApi } from "../../api/platform";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { PageHeader } from "../../components/ui/PageHeader";
import { CrmPagination } from "../../components/crm/CrmPagination";
import { ErrorState, LoadingState, EmptyState } from "../../components/ui/StateViews";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";
import { useI18n } from "../../lib/i18n";

export function PlatformMerchantsPage() {
  const { t, language } = useI18n();
  const location = useLocation();
  const [params, setParams] = useSearchParams();
  const query = params.get("search") || "";
  const page = Math.max(1, Number(params.get("page")) || 1);
  const pageSize = [10, 20, 30, 50, 100].includes(Number(params.get("page_size"))) ? Number(params.get("page_size")) : 20;
  const search = useDebouncedValue(query, 250);
  const merchants = useQuery({ queryKey: ["platform-merchants", search, page, pageSize], queryFn: () => platformApi.merchants({ search, page, page_size: pageSize }) });
  const locale = language === "kk" ? "kk-KZ" : language === "en" ? "en-US" : "ru-RU";
  function update(values: Record<string, string>) {
    setParams(current => { const next = new URLSearchParams(current); for (const [key, value] of Object.entries(values)) { if (value) next.set(key, value); else next.delete(key); } return next; }, { replace: true });
  }
  const rows = merchants.data?.results || [];
  return <div className="space-y-4" data-testid="platform-merchants-ready">
    <PageHeader title={t("platform.merchants.title")} />
    <div className="flex flex-wrap items-center gap-2">
      <Input aria-label={t("platform.merchants.search")} placeholder={t("platform.merchants.search")} value={query} onChange={event => update({ search: event.target.value, page: "" })} className="w-full sm:w-80" />
      {query && <Button variant="ghost" onClick={() => update({ search: "", page: "" })}>{t("tasks.resetFilters")}</Button>}
      <Button variant="secondary" onClick={() => merchants.refetch()} isLoading={merchants.isFetching}>{t("platform.merchantDetail.refresh")}</Button>
    </div>
    {merchants.isPending ? <LoadingState scope="page" /> : merchants.isError ? <ErrorState error={merchants.error} message={t("platform.merchants.error")} action={<Button variant="secondary" onClick={() => merchants.refetch()}>{t("platform.merchantDetail.refresh")}</Button>} /> : !rows.length ? <EmptyState title={t("platform.merchants.emptyTitle")} description={t("platform.merchants.emptyText")} /> : <Card>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[920px] text-left text-sm">
          <thead className="border-b border-platforma-border bg-surface-muted text-xs text-platforma-subtle"><tr>
            {["merchant", "owner", "status", "operations", "supportWorkflow", "usage", "created"].map(key => <th scope="col" className="px-4 py-3 font-medium" key={key}>{t(`platform.merchants.${key}`)}</th>)}
          </tr></thead>
          <tbody>{rows.map(merchant => <tr key={merchant.id} className="border-b border-platforma-border last:border-0 hover:bg-surface-hover">
            <td className="px-4 py-3"><Link state={{ returnTo: location.pathname + location.search }} to={`/platform/merchants/${merchant.id}`} className="platforma-focus-ring font-semibold text-platforma-text hover:text-brand-700">{merchant.name}</Link><p className="mt-1 text-xs text-platforma-faint">ID {merchant.id}</p></td>
            <td className="px-4 py-3"><p>{merchant.owner.full_name || t("platform.common.noName")}</p><p className="mt-1 text-xs text-platforma-subtle">{merchant.owner.email}</p></td>
            <td className="px-4 py-3"><p>{merchant.status}</p><p className="mt-1 text-xs text-platforma-subtle">{merchant.plan?.name || t("platform.merchants.noPlan")} · {merchant.subscription_status || t("platform.merchants.noSubscription")}</p></td>
            <td className="px-4 py-3 text-xs leading-6 text-platforma-subtle"><p>{t("platform.merchants.opsLeads", { leads: merchant.operations?.lead_count ?? 0, new: merchant.operations?.new_leads ?? 0 })}</p><p>{t("platform.merchants.opsInbox", { unread: merchant.operations?.unread_conversations ?? 0, handoff: merchant.operations?.handoff_conversations ?? 0 })}</p><p>{t("platform.merchants.opsSources", { ok: merchant.operations?.connected_connectors ?? 0, fail: merchant.operations?.failed_connectors ?? 0 })}</p></td>
            <td className="max-w-64 px-4 py-3"><p className="text-xs font-medium">{t("platform.merchants.supportPriority", { priority: merchant.support_workflow?.priority || "low" })}</p><p className="mt-1 text-xs leading-5 text-platforma-subtle">{merchant.support_workflow?.summary}</p></td>
            <td className="px-4 py-3 text-xs text-platforma-subtle">{t("platform.merchants.usageText", { ai: merchant.usage_summary.find(item => item.metric === "ai_requests")?.value ?? 0, messages: merchant.usage_summary.find(item => item.metric === "bot_messages")?.value ?? 0 })}</td>
            <td className="whitespace-nowrap px-4 py-3 text-xs text-platforma-subtle">{merchant.created_at ? new Date(merchant.created_at).toLocaleDateString(locale) : "—"}</td>
          </tr>)}</tbody>
        </table>
      </div>
      <CrmPagination compact shown={rows.length} total={merchants.data?.count || 0} page={page} pageSize={pageSize} onPageChange={value => update({ page: String(value) })} onPageSizeChange={value => update({ page_size: String(value), page: "" })} previousLabel={t("pagination.previous")} nextLabel={t("pagination.next")} />
    </Card>}
  </div>;
}

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router";
import { supportApi } from "../../api/support";
import { CrmPagination } from "../../components/crm/CrmPagination";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Input } from "../../components/ui/Input";
import { PageHeader } from "../../components/ui/PageHeader";
import { Select } from "../../components/ui/Select";
import { EmptyState, LoadingState } from "../../components/ui/StateViews";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";
import { useI18n } from "../../lib/i18n";
import type { SupportScope } from "../../types/support";
import { SupportClinicPicker } from "./SupportClinicPicker";
import { SupportCreateDialog } from "./SupportCreateDialog";
import { SupportError, SupportStatusBadge, retainSupportData, supportDate, supportStatuses } from "./SupportUI";

export function SupportListPage({ platform = false }: { platform?: boolean }) {
  const { t, language } = useI18n();
  const active = useActiveBusiness();
  const navigate = useNavigate();
  const location = useLocation();
  const [params, setParams] = useSearchParams();
  const [creating, setCreating] = useState(false);
  const root = platform ? "/platform/support" : "/app/support";
  const scope: SupportScope = { platform, business: platform ? undefined : active.business?.id };
  const search = params.get("search") || "";
  const needle = useDebouncedValue(search, 250);
  const status = params.get("status") || "";
  const assignee = platform ? params.get("assignee") || "" : "";
  const business = platform ? Number(params.get("business")) || undefined : undefined;
  const page = Math.max(1, Math.floor(Number(params.get("page")) || 1));
  const pageSize = [10, 20, 30, 50, 100].includes(Number(params.get("page_size"))) ? Number(params.get("page_size")) : 20;
  const unread = params.get("unread") === "true";
  const list = useQuery({
    queryKey: ["support", platform ? "platform" : "clinic", scope.business, "list", needle, status, assignee, business, page, pageSize, unread],
    queryFn: () => supportApi.list(scope, { search: needle, status, ...(platform ? { assignee, business } : {}), page, page_size: pageSize, unread }),
    enabled: platform || Boolean(scope.business), refetchInterval: 30_000,
  });
  function update(values: Record<string, string>) {
    setParams(current => { const next = new URLSearchParams(current); for (const [key, value] of Object.entries(values)) { if (value) next.set(key, value); else next.delete(key); } return next; }, { replace: true });
  }
  if (!platform && active.isLoading) return <LoadingState scope="page" />;
  if (!platform && active.isError) return <SupportError error={active.error} retry={() => active.refetch()} />;
  if (!platform && !scope.business) return <EmptyState title={t("supportCases.noBusiness")} />;
  const rows = list.data?.results || [];
  const filtered = Boolean(search || status || assignee || business || unread);
  const createButton = <Button id="support-create-button" onClick={() => setCreating(true)}>{t("supportCases.create")}</Button>;
  return <div className="space-y-4" data-testid="support-list">
    {platform ? <PageHeader title={t("supportCases.title")} actions={createButton} /> : <div className="flex justify-end">{createButton}</div>}
    <div className="flex flex-wrap items-end gap-3">
      <Input label={t("supportCases.search")} value={search} onChange={event => update({ search: event.target.value, page: "" })} maxLength={200} className="sm:w-72" />
      <Select label={t("supportCases.statusLabel")} value={status} onChange={event => update({ status: event.target.value, page: "" })} className="sm:w-56"
        options={[{ value: "", label: t("supportCases.allStatuses") }, { value: "active", label: t("supportCases.active") }, ...supportStatuses.map(value => ({ value, label: t(`supportCases.status.${value}`) }))]} />
      {platform && <Select label={t("supportCases.assigneeFilter")} value={assignee} onChange={event => update({ assignee: event.target.value, page: "" })} className="sm:w-56"
        options={[{ value: "", label: t("supportCases.allAssignees") }, ...["me", "unassigned", "unavailable"].map(value => ({ value, label: t(`supportCases.filter.${value}`) }))]} />}
      <label className="flex min-h-11 items-center gap-2 text-sm"><input type="checkbox" className="platforma-focus-ring size-4" checked={unread} onChange={event => update({ unread: event.target.checked ? "true" : "", page: "" })} />{t("supportCases.unreadOnly")}</label>
      <Button variant="secondary" onClick={() => list.refetch()} isLoading={list.isFetching}>{t("common.refresh")}</Button>
      {filtered && <Button variant="ghost" onClick={() => setParams({})}>{t("tasks.resetFilters")}</Button>}
    </div>
    {platform && <details className="rounded-control border border-platforma-border p-3" open={Boolean(business) || undefined}>
      <summary className="platforma-focus-ring cursor-pointer text-sm font-medium">{t("supportCases.clinicFilter")}{business ? ` · #${business}` : ""}</summary>
      <div className="mt-3 max-w-md"><SupportClinicPicker value={business} onChange={value => update({ business: value ? String(value) : "", page: "" })} /></div>
    </details>}
    {list.isError && <SupportError error={list.error} retry={() => list.refetch()} />}
    {list.isPending ? <LoadingState scope="page" /> : list.isError && (!list.data || !retainSupportData(list.error)) ? null : !rows.length ? <EmptyState title={t(filtered ? "supportCases.noMatches" : "supportCases.empty")} /> : <Card>
      <table className="block w-full text-left text-sm md:table">
        <thead className="sr-only border-b border-platforma-border bg-surface-muted text-platforma-subtle md:not-sr-only md:table-header-group"><tr>
          {["subject", ...(platform ? ["clinic"] : []), "statusLabel", "assignee", "updated"].map(key => <th scope="col" key={key} className="px-4 py-3 font-medium">{t(`supportCases.${key}`)}</th>)}
        </tr></thead>
        <tbody className="block md:table-row-group">{rows.map(item => <tr key={item.id} className="grid grid-cols-2 gap-y-2 border-b border-platforma-border py-3 last:border-0 hover:bg-surface-hover md:table-row md:py-0" data-testid="support-case-row">
          <td className="col-span-2 min-w-0 px-4 py-2 align-top md:py-4"><Link to={`${root}/${item.id}`} state={{ returnTo: location.pathname + location.search }} className="platforma-focus-ring break-words font-semibold text-platforma-text hover:text-brand-700">{item.subject}</Link><p className="mt-1 text-xs text-platforma-subtle">{item.number} · {item.author.name}</p>{item.unread_count > 0 && <span className="mt-2 inline-block"><Badge variant="info">{t("supportCases.unreadCount", { count: item.unread_count })}</Badge></span>}</td>
          {platform && <td className="min-w-0 break-words px-4 py-2 align-top md:py-4">{item.business_name}</td>}
          <td className="px-4 py-2 align-top md:py-4"><SupportStatusBadge status={item.status} /></td>
          <td className="min-w-0 break-words px-4 py-2 align-top md:py-4"><p className="text-xs text-platforma-faint md:hidden">{t("supportCases.assignee")}</p>{item.assignee?.name || t("supportCases.filter.unassigned")}{item.assignee?.available === false && <p className="mt-1 text-xs text-platforma-warning">{t("supportCases.assigneeUnavailable")}</p>}</td>
          <td className="px-4 py-2 align-top text-xs text-platforma-subtle md:py-4">{supportDate(item.updated_at, language, item.business_timezone)}<p className="mt-1">{item.business_timezone}</p></td>
        </tr>)}</tbody>
      </table>
      <CrmPagination compact shown={rows.length} total={list.data?.count || 0} page={page} pageSize={pageSize} onPageChange={value => update({ page: String(value) })} onPageSizeChange={value => update({ page_size: String(value), page: "" })} previousLabel={t("pagination.previous")} nextLabel={t("pagination.next")} />
    </Card>}
    {creating && <SupportCreateDialog scope={scope} initialBusiness={business} onClose={() => setCreating(false)} onCreated={item => { setCreating(false); navigate(`${root}/${item.id}`, { state: { returnTo: location.pathname + location.search } }); }} />}
  </div>;
}

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useLocation } from "react-router";
import { platformApi } from "../../api/platform";
import { normalizeAppError } from "../../api/appError";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { DateRangePicker, isCalendarDate } from "../../components/ui/DateRangePicker";
import { Dialog } from "../../components/ui/Overlay";
import { LoadingState, EmptyState } from "../../components/ui/StateViews";
import { StatusNotice } from "../../components/ui/StatusNotice";
import { CrmPagination } from "../../components/crm/CrmPagination";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";
import { useI18n } from "../../lib/i18n";
import type { OperationFilters, OperationSource } from "../../types/platformOperations";
import { incidentPath } from "../support/SupportIncidents";
import { PlatformLoadError, platformDate, valueOrUnknown } from "./PlatformData";

export function OperationsWorklist({ section, params, update }: {
  section: "incidents" | "connectors" | "history"; params: URLSearchParams;
  update: (values: Record<string, string>) => void;
}) {
  const { t, language } = useI18n();
  const location = useLocation();
  const search = params.get("search") || "";
  const needle = useDebouncedValue(search, 250);
  const history = section === "history", incidents = section === "incidents";
  const source: OperationSource = history ? (["automations", "integrations", "webhooks"].find(value => value === params.get("source")) as OperationSource || "automations") : section;
  const page = Math.max(1, Math.floor(Number(params.get("page")) || 1));
  const pageSize = [10, 20, 30, 50, 100].includes(Number(params.get("page_size"))) ? Number(params.get("page_size")) : 20;
  const today = new Date().toISOString().slice(0, 10);
  const defaultStart = new Date(`${today}T00:00:00Z`); defaultStart.setUTCDate(defaultStart.getUTCDate() - 29);
  const from = params.get("date_from") || defaultStart.toISOString().slice(0, 10), to = params.get("date_to") || today;
  const [periodOpen, setPeriodOpen] = useState(false), [draft, setDraft] = useState({ from, to });
  const filters: OperationFilters = { source, search: needle, page, page_size: pageSize,
    ...(params.get("business") ? { business: Number(params.get("business")) } : {}),
    ...(incidents ? { component: params.get("component") || undefined, freshness: params.get("freshness") || undefined } : {}),
    ...(history ? { date_from: from, date_to: to } : {}) };
  const result = useQuery({ queryKey: ["platform-worklist", filters], queryFn: () => platformApi.operationsWorklist(filters), refetchInterval: 30_000 });
  const forbidden = result.isError && !["offline", "temporary", "provider", "rate_limit", "internal"].includes(normalizeAppError(result.error).category);
  const data = forbidden ? undefined : result.data;
  const validPeriod = isCalendarDate(draft.from) && isCalendarDate(draft.to) && draft.from <= draft.to && draft.to <= today && (Date.parse(draft.to)-Date.parse(draft.from))/86400000 <= 365;
  return <div className="space-y-4">
    <div className="flex flex-wrap items-end gap-3">
      {params.get("business") && <p className="text-sm">{t("platform.merchants.merchant")} #{params.get("business")}</p>}
      <Input aria-label={t("operationsWorkspace.search")} placeholder={t("operationsWorkspace.search")} value={search} onChange={event => update({ search: event.target.value, business: "", page: "" })} className="w-full sm:w-72" />
      {incidents && <>
        <Select aria-label={t("supportIncidents.source")} value={params.get("component") || ""} onChange={event => update({ component: event.target.value, page: "" })} options={[{ value: "", label: t("operationsWorkspace.allComponents") }, ...["automations", "notifications", "exports", "files"].map(value => ({ value, label: t(`serviceStatus.component.${value}`) }))]} />
        <Select aria-label={t("operationsWorkspace.freshness")} value={params.get("freshness") || ""} onChange={event => update({ freshness: event.target.value, page: "" })} options={["", "fresh", "unknown"].map(value => ({ value, label: t(`operationsWorkspace.${value || "allObservations"}`) }))} />
      </>}
      {history && <>
        <Select aria-label={t("operationsWorkspace.source")} value={source} onChange={event => update({ source: event.target.value, page: "" })} options={["automations", "integrations", "webhooks"].map(value => ({ value, label: t(`operationsWorkspace.${value}`) }))} />
        <Button variant="secondary" onClick={() => { setDraft({ from, to }); setPeriodOpen(true); }} aria-label={t("operationsWorkspace.period")}>{from} — {to} · UTC</Button>
      </>}
      <Button variant="secondary" onClick={() => result.refetch()} isLoading={result.isFetching}>{t("common.refresh")}</Button>
      {(search || params.get("business") || params.get("component") || params.get("freshness") || params.get("date_from") || params.get("date_to")) && <Button variant="ghost" onClick={() => update({ search: "", business: "", component: "", freshness: "", date_from: "", date_to: "", page: "" })}>{t("tasks.resetFilters")}</Button>}
    </div>
    {data && <p className="text-xs text-platforma-subtle">{t("operationsWorkspace.updated", { time: platformDate(data.generated_at, language) })}</p>}
    {result.isError && <PlatformLoadError error={result.error} message={t("platform.operations.error")} onRetry={() => result.refetch()} />}
    {result.isError && page > 1 && <Button variant="secondary" onClick={() => update({ page: "" })}>{t("pagination.previous")} · 1</Button>}
    {result.isPending ? <LoadingState scope="page" /> : data && <>
      {!!data.unavailable_sources.length && <StatusNotice compact tone="warning" title={t("platform.workspace.partial")} />}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-base font-semibold">{t(`operationsWorkspace.${incidents ? "backgroundEpisodes" : history ? "recordedFailures" : "connectors"}`)}</h2>
        <p className="text-sm tabular-nums" data-testid="operations-count">{t("operationsWorkspace.count", { count: valueOrUnknown(data.count) })}</p>
      </div>
      {data.count == null ? <EmptyState title={t("platform.workspace.unknown")} /> : !data.results.length ? <EmptyState title={t("operationsWorkspace.empty")} /> : <Card>
        <table className="block w-full text-left text-sm md:table" data-testid="operations-table">
          <thead className="sr-only border-b border-platforma-border bg-surface-muted text-xs md:not-sr-only md:table-header-group"><tr>{["platform.merchants.merchant", "operationsWorkspace.source", "operationsWorkspace.observation", "operationsWorkspace.time", "operationsWorkspace.actions"].map(key => <th scope="col" key={key} className="px-4 py-3 font-medium">{t(key)}</th>)}</tr></thead>
          <tbody className="block md:table-row-group">{data.results.map(row => <tr key={row.id} data-testid="operations-row" className="grid grid-cols-2 gap-y-2 border-b border-platforma-border py-3 last:border-0 hover:bg-surface-hover md:table-row">
            <td className="col-span-2 min-w-0 px-4 py-2 align-top md:py-4">{row.business_id ? <Link state={{ returnTo: location.pathname+location.search }} to={`/platform/merchants/${row.business_id}`} className="platforma-focus-ring break-words font-semibold text-brand-700">{row.business_name} · #{row.business_id}</Link> : t("platform.operations.noBusiness")}</td>
            <td className="min-w-0 break-words px-4 py-2 align-top md:py-4"><p>{row.component ? t(`serviceStatus.component.${row.component}`) : row.provider || row.kind}</p><p className="mt-1 text-xs text-platforma-subtle">#{incidents ? row.episode : row.id}{row.provider && row.kind ? ` · ${row.kind}` : ""}</p></td>
            <td className="min-w-0 px-4 py-2 align-top md:py-4"><span className={row.status === "unknown" ? "text-platforma-subtle" : "text-platforma-warning"}>{t(incidents ? `platform.workspace.service.${row.status}` : `operationsWorkspace.status.${row.status}`)}</span>{incidents && <p className="mt-1 text-xs">{t("serviceStatus.platform.overdue", { count: row.affected_count ?? 0 })}</p>}{row.attempts !== undefined && <p className="mt-1 text-xs">{t("operationsWorkspace.attempts", { count: row.attempts })}</p>}</td>
            <td className="min-w-0 px-4 py-2 align-top text-xs md:py-4">{incidents && <p>{t("supportIncidents.started")}: {platformDate(row.started_at, language)}</p>}<p className="mt-1 text-platforma-subtle">{incidents && `${t("supportIncidents.observed")}: `}{platformDate(row.observed_at || row.occurred_at, language)}</p></td>
            <td className="col-span-2 min-w-0 px-4 py-2 align-top md:py-4">{row.business_id && (incidents ? <Link state={{ returnTo: location.pathname+location.search }} className="platforma-focus-ring inline-flex min-h-10 items-center text-brand-700" to={incidentPath(row.business_id, row.component!, row.episode!)}>{t("supportIncidents.open")} · {t("operationsWorkspace.linkedCases", { count: valueOrUnknown(row.linked_cases) })}</Link> : <Link className="platforma-focus-ring inline-flex min-h-10 items-center text-brand-700" to={`/platform/support?business=${row.business_id}`}>{t("supportCases.title")}</Link>)}</td>
          </tr>)}</tbody>
        </table>
        <CrmPagination compact shown={data.results.length} total={data.count} page={page} pageSize={pageSize} onPageChange={value => update({ page: String(value) })} onPageSizeChange={value => update({ page_size: String(value), page: "" })} previousLabel={t("pagination.previous")} nextLabel={t("pagination.next")} />
      </Card>}
    </>}
    <Dialog title={t("operationsWorkspace.period")} open={periodOpen} onClose={() => setPeriodOpen(false)} size="sm"><div className="space-y-4">
      <DateRangePicker label={t("operationsWorkspace.period")} value={draft} onChange={setDraft} today={today} />
      <div className="flex justify-end gap-2"><Button variant="ghost" onClick={() => setPeriodOpen(false)}>{t("common.cancel")}</Button><Button disabled={!validPeriod} onClick={() => { update({ date_from: draft.from, date_to: draft.to, page: "" }); setPeriodOpen(false); }}>{t("crmFilters.apply")}</Button></div>
    </div></Dialog>
  </div>;
}

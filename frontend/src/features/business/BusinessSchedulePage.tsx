import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { branchesApi, type Branch, type BranchConfiguration } from "../../api/branches";
import { resourcesApi } from "../../api/resources";
import { scheduleExceptionsApi, workingHoursApi } from "../../api/workingHours";
import { usePageHeader } from "../../components/layout/PageHeaderContext";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { Select } from "../../components/ui/Select";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { usePageLoading } from "../../components/ui/PageLoadingBoundary";
import { Tabs } from "../../components/ui/Tabs";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { cn } from "../../lib/cn";
import { todayInTimeZone } from "../../lib/format";
import { useI18n } from "../../lib/i18n";
import type { Id } from "../../types";
import { BusinessWorkspaceNav } from "./components/BusinessWorkspaceNav";
import { ScheduleDayDialog } from "./components/ScheduleDayDialog";
import { BranchScheduleEditor } from "./components/BranchScheduleEditor";
import { useActionConfirm } from "../../components/actions/ActionConfirmProvider";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { scheduleCell, shiftDate, validDate, weekDates, weekdayKeys } from "./schedule";

export type ScheduleTarget = { id: Id | null; name: string; kind: "opening" | "staff" | "physical"; active: boolean };

export function BusinessSchedulePage({ embedded = false }: { embedded?: boolean }) {
  const { t } = useI18n();
  const { business } = useActiveBusiness();
  const { setPageHeader } = usePageHeader();
  const [params, setParams] = useSearchParams();
  const branches = useQuery({ queryKey: ["branches", business?.id], queryFn: () => branchesApi.listAll({ business: business!.id }), enabled: !!business });
  useEffect(() => { setPageHeader({ title: t("nav.business") }); return () => setPageHeader(null); }, [setPageHeader, t]);
  const available = (branches.data || []).filter(branch => !branch.archived_at && (branch.can_work || branch.can_manage));
  usePageLoading(branches.isLoading);
  const selected = available.find(branch => String(branch.id) === params.get("branch")) || available[0];
  return <div className="min-w-0 space-y-4">
    {!embedded && <BusinessWorkspaceNav />}
    {branches.isPending ? <LoadingState /> : branches.error ? <ErrorState error={branches.error} action={<Button onClick={() => void branches.refetch()}>{t("common.retry")}</Button>} /> : selected && business ? <>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h2 className="text-base font-semibold">{t("nav.workingHours")}</h2>
        <div className="w-full sm:w-72"><Select label={t("branches.branch")} value={selected.id} options={available.map(branch => ({ value: branch.id, label: branch.name }))}
          onChange={event => setParams(previous => { const next = new URLSearchParams(previous); next.set("branch", event.target.value); next.delete("resource"); return next; })} /></div>
      </div>
      <ScheduleWorkspace key={selected.id} branch={selected} branches={available} timeZone={business.timezone} embedded={embedded} />
    </> : <Link className="text-sm text-brand-700 underline" to="/app/business/branches">{t("branches.empty")}</Link>}
  </div>;
}

function ScheduleWorkspace({ branch, branches, timeZone, embedded }: { branch: Branch; branches: Branch[]; timeZone: string; embedded: boolean }) {
  const { t, language } = useI18n();
  const [params, setParams] = useSearchParams();
  const today = todayInTimeZone(timeZone);
  const date = validDate(params.get("date"), today);
  const dates = weekDates(date);
  const [search, setSearch] = useState("");
  const [edit, setEdit] = useState<{ target: ScheduleTarget; date: string; weekly: boolean } | null>(null);
  const [travel, setTravel] = useState(false);
  const [travelDirty, setTravelDirty] = useState(false);
  const confirm = useActionConfirm();
  const config = useQuery({ queryKey: [branch.can_manage ? "branch-configuration" : "branch-catalog", branch.id], queryFn: async (): Promise<BranchConfiguration> => {
    if (branch.can_manage) return branchesApi.configuration(branch.id);
    const data = await branchesApi.catalog(branch.id);
    return { ...data, days: data.days || [], travel: [], physical_resources: data.physical_resources || [], resource_requirements: data.resource_requirements || [] };
  } });
  const resources = useQuery({ queryKey: ["resources", "business-schedule", branch.business, branch.id], queryFn: () => resourcesApi.listAll({ business: branch.business, branch: branch.id }) });
  const hours = useQuery({ queryKey: ["working-hours", "business-schedule", branch.business], queryFn: () => workingHoursApi.list({ business: branch.business }), enabled: !!branch.uses_business_defaults });
  const exceptions = useQuery({ queryKey: ["schedule-exceptions", "business-schedule", branch.business], queryFn: () => scheduleExceptionsApi.list({ business: branch.business }), enabled: !!branch.uses_business_defaults });
  const cache = useQueryClient();
  const travelMutation = useMutation({ mutationFn: (operation: () => Promise<unknown>) => operation(), onSuccess: async () => {
    await Promise.all(["branch-configuration", "branch-catalog", "available-slots"].map(key => cache.invalidateQueries({ queryKey: [key] })));
  } });
  const view = ["opening", "physical"].includes(params.get("view") || "") ? params.get("view")! : "staff";
  const setDate = (value: string) => setParams(previous => { const next = new URLSearchParams(previous); next.set("date", value); return next; });
  const error = config.error || resources.error || (branch.uses_business_defaults && (hours.error || exceptions.error));
  if (config.isPending || resources.isPending || (branch.uses_business_defaults && (hours.isPending || exceptions.isPending))) return <LoadingState initial />;
  if (error) return <ErrorState error={error} action={<Button onClick={() => void Promise.all([config.refetch(), resources.refetch(), ...(branch.uses_business_defaults ? [hours.refetch(), exceptions.refetch()] : [])])}>{t("common.retry")}</Button>} />;
  if (!config.data) return null;
  const targets: ScheduleTarget[] = view === "opening" ? [{ id: null, name: branch.name, kind: "opening", active: branch.is_active }] : (resources.data || [])
    .filter(resource => !resource.retired_at && (view === "staff" ? resource.resource_type === "staff" : resource.resource_type !== "staff"))
    .filter(resource => !embedded || view === "staff" || ["room", "hall", "box"].includes(resource.resource_type))
    .filter(resource => view !== "staff" || branch.uses_business_defaults || config.data!.assignments.some(row => row.resource === resource.id && row.is_active))
    .filter(resource => resource.name.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase()))
    .map(resource => ({ id: resource.id, name: resource.name, kind: view as "staff" | "physical", active: resource.is_active }));
  if (embedded && view !== "opening") targets.unshift({ id: null, name: branch.name, kind: "opening", active: branch.is_active });
  const shortDate = (value: string) => language === "kk" ? `${Number(value.slice(-2))} ${t(`calendar.month.${Number(value.slice(5, 7))}`)}` : new Intl.DateTimeFormat(language === "ru" ? "ru-RU" : "en-GB", { day: "numeric", month: "short", timeZone: "UTC" }).format(new Date(`${value}T12:00:00Z`));
  const cell = (target: ScheduleTarget, value: string) => scheduleCell({ automatic: !!branch.uses_business_defaults, config: config.data!, hours: hours.data || [], exceptions: exceptions.data || [], resource: target.id, date: value });
  function renderCell(target: ScheduleTarget, value: string) {
    const state = cell(target, value);
    return <button type="button" className={cn("platforma-focus-ring flex min-h-20 w-full flex-col items-center justify-center gap-1 rounded-control px-2 py-3 text-sm tabular-nums hover:bg-surface-hover", value === today && "bg-brand-50/50")}
      aria-label={`${target.name}, ${shortDate(value)}, ${state.absent ? t("branches.absences") : state.intervals.map(interval => `${interval.start}–${interval.end}`).join(", ") || t(state.configured ? "workingHours.dayOff" : "branches.scheduleMissing")}`}
      onClick={() => setEdit({ target, date: value, weekly: !!branch.uses_business_defaults && target.id === null })}>
      {state.absent ? <span className="text-platforma-subtle">{t("branches.absences")}</span> : state.intervals.length ? state.intervals.map((interval, index) => <span key={index}>{interval.start}–{interval.end}</span>) : <span className="text-platforma-subtle">{state.configured ? t("workingHours.dayOff") : "—"}</span>}
      {state.override && <span className="text-xs text-brand-700">{t("branches.dateOverride")}</span>}
    </button>;
  }
  return <div className="space-y-4">
    {embedded && <p className="text-xs text-platforma-subtle">{timeZone}</p>}
    <Tabs value={view} onChange={value => setParams(previous => { const next = new URLSearchParams(previous); next.set("view", value); next.delete("resource"); return next; })} appearance="underline" ariaLabel={t("nav.workingHours")}
      options={[{ value: "staff", label: t(embedded ? "management.specialists" : "business.staff") }, { value: "physical", label: t(embedded ? "management.rooms" : "branches.physicalResources") }, ...(!embedded || view === "opening" ? [{ value: "opening", label: t("branches.openingHours") }] : [])]} />
    <div className="flex flex-wrap items-end gap-2">
      <div className="flex items-center gap-2">
      <Button variant="secondary" aria-label={t("business.previousWeek")} onClick={() => setDate(shiftDate(date, -7))}><ChevronLeft size={18} /></Button>
      <Button variant="secondary" onClick={() => setDate(today)}>{t("business.today")}</Button>
      <Button variant="secondary" aria-label={t("business.nextWeek")} onClick={() => setDate(shiftDate(date, 7))}><ChevronRight size={18} /></Button>
      </div>
      <div className="w-full min-w-0 sm:w-44"><Input label={t("appointment.date")} type="date" value={date} onChange={event => event.target.value && setDate(validDate(event.target.value, today))} /></div>
      <p className="w-full py-1 text-sm text-platforma-subtle sm:w-auto sm:py-2">{shortDate(dates[0])} – {shortDate(dates[6])}</p>
      {branch.can_manage && <Button variant="secondary" disabled={!targets.length} onClick={() => setEdit({ target: targets.find(target => String(target.id) === params.get("resource")) || targets[0], date, weekly: true })}>{t("business.weekTemplate")}</Button>}
      {branches.length > 1 && branch.can_manage && <Button variant="secondary" onClick={() => setTravel(true)}>{t("branches.travel")}</Button>}
    </div>
    {view !== "opening" && <div className="max-w-md"><Input label={t("resources.searchPlaceholder")} value={search} onChange={event => setSearch(event.target.value)} /></div>}
    <div className="flex gap-1 overflow-x-auto pb-1 md:hidden" aria-label={t("branches.weekday")}>
      {dates.map((value, index) => <button key={value} type="button" aria-pressed={value === date} onClick={() => setDate(value)} className={cn("platforma-focus-ring flex min-h-12 min-w-0 flex-1 flex-col items-center justify-center rounded-control border text-xs", value === date ? "border-brand-200 bg-brand-50 text-brand-700" : "border-platforma-border bg-surface-card")}><span>{t(weekdayKeys[index])}</span><span className="mt-1 font-semibold">{Number(value.slice(-2))}</span></button>)}
    </div>
    {targets.length ? <>
      <div className="hidden overflow-x-auto rounded-card border border-platforma-border bg-surface-card md:block">
        <table className="w-full table-fixed text-sm"><caption className="sr-only">{branch.name} · {shortDate(dates[0])} – {shortDate(dates[6])}</caption>
          <thead><tr className="border-b border-platforma-border"><th scope="col" className="w-44 p-3 text-left font-semibold">{t(view === "opening" ? "branches.branch" : view === "staff" ? embedded ? "management.specialists" : "business.staff" : embedded ? "management.rooms" : "nav.resources")}</th>{dates.map((value, index) => <th scope="col" key={value} className="p-2 font-medium"><span className="block">{t(weekdayKeys[index])}</span><span className="mt-1 block text-xs text-platforma-subtle">{shortDate(value)}</span></th>)}</tr></thead>
          <tbody>{targets.map(target => <tr key={target.id ?? "opening"} className="border-b border-platforma-border last:border-0"><th scope="row" className="break-words p-3 text-left font-medium">{target.name}{!target.active && <span className="mt-1 block text-xs text-platforma-subtle">{t("branches.paused")}</span>}</th>{dates.map(value => <td key={value} className="border-l border-platforma-border p-1 align-top">{renderCell(target, value)}</td>)}</tr>)}</tbody>
        </table>
      </div>
      <div className="divide-y divide-platforma-border rounded-card border border-platforma-border bg-surface-card md:hidden">
        {targets.map(target => <div key={target.id ?? "opening"} className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)] items-center gap-3 p-3"><p className="break-words text-sm font-semibold">{target.name}{!target.active && <span className="block text-xs font-normal text-platforma-subtle">{t("branches.paused")}</span>}</p>{renderCell(target, date)}</div>)}
      </div>
    </> : <div className="rounded-card border border-platforma-border bg-surface-card p-6 text-sm"><p>{t("resources.noResultsTitle")}</p><Link className="mt-3 inline-flex min-h-11 items-center text-brand-700 underline" to={`/app/business/${view === "staff" ? "staff" : "resources"}?branch=${branch.id}`}>{t(view === "staff" ? "business.staff" : "branches.physicalResources")}</Link></div>}
    {edit && <ScheduleDayDialog branch={branch} target={edit.target} targets={targets} date={edit.date} weekly={edit.weekly} config={config.data} hours={hours.data || []} exceptions={exceptions.data || []} onClose={() => setEdit(null)} />}
    <Modal title={t("branches.travel")} open={travel} onClose={async () => {
      if (travelMutation.isPending) return;
      if (travelDirty && !(await confirm({ title: t("workingHours.discardChanges"), confirmLabel: t("actions.discardChanges"), tone: "warning" })).confirmed) return;
      setTravelDirty(false); setTravel(false);
    }}>
      {travelMutation.error && <ErrorState error={travelMutation.error} />}
      <BranchScheduleEditor tab="travel" branch={branch} branches={branches} config={config.data} save={operation => travelMutation.mutateAsync(operation)} disabled={travelMutation.isPending || !branch.is_active} onDirtyChange={setTravelDirty} />
    </Modal>
  </div>;
}

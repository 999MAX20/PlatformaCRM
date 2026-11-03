import { ArrowDownWideNarrow, ArrowUpWideNarrow, CalendarDays, SlidersHorizontal, X } from "lucide-react";
import { useRef, useState } from "react";
import { Link, type SetURLSearchParams } from "react-router";
import { Button } from "../../components/ui/Button";
import { RecordsPeriodPanel } from "./RecordsPeriodPanel";
import { RecordsSearch } from "./RecordsSearch";
import { Modal } from "../../components/ui/Modal";
import { Select } from "../../components/ui/Select";
import { useI18n } from "../../lib/i18n";
import { patchRecordFilters, recordAdvancedKeys, recordWorkspaceParams, recordWorkflows, resetRecordFilters } from "./recordFilters";

type Option = { value: string | number; label: string };
type Props = {
  today: string;
  params: URLSearchParams;
  setParams: SetURLSearchParams;
  filters: ReturnType<typeof recordWorkspaceParams>;
  summary?: Partial<Record<typeof recordWorkflows[number], number>>;
  resources: Option[];
  branches: Option[];
  members: Option[];
};

export function RecordsToolbar({ today, params, setParams, filters, summary, resources, branches, members }: Props) {
  const { t, language } = useI18n();
  const [dialog, setDialog] = useState<"filters" | null>(null);
  const [periodOpen, setPeriodOpen] = useState(false);
  const periodTrigger = useRef<HTMLButtonElement>(null);
  const closePeriod = () => { setPeriodOpen(false); periodTrigger.current?.focus(); };
  const [draft, setDraft] = useState<Record<string, string>>({});
  const update = (patch: Record<string, string>) => setParams(current => patchRecordFilters(current, patch));
  const reset = () => setParams(current => resetRecordFilters(current, today));
  const fields = [
    { key: "resource", label: t("records.specialist"), options: resources },
    { key: "responsible_user", label: t("appointment.responsible"), options: members },
    { key: "confirmed", label: t("records.confirmation"), options: [{ value: "true", label: t("appointments.confirmed") }, { value: "false", label: t("records.unconfirmed") }] },
    { key: "branch", label: t("records.branch"), options: branches },
  ];
  const chips = fields.filter(field => params.get(field.key)).map(field => ({ key: field.key, label: field.label, value: field.options.find(option => String(option.value) === params.get(field.key))?.label || `#${params.get(field.key)}` }));
  if (filters.client) chips.push({ key: "client", label: t("appointment.client"), value: `#${filters.client}` });
  if (filters.attention) chips.push({ key: "attention", label: t("records.pendingResult"), value: "" });
  const hasFilters = chips.length > 0 || !!filters.q || !!filters.workflow || params.has("from") || params.has("to") || filters.ordering !== "start_at";
  const from = filters.start_from || "";
  const to = params.get("to") || from;
  const formatDay = (day: string) => {
    const date = new Date(`${day}T12:00:00Z`);
    return Number.isFinite(date.getTime()) ? new Intl.DateTimeFormat(language === "kk" ? "kk-KZ" : language === "en" ? "en-GB" : "ru-RU", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }).format(date) : day;
  };
  const period = from === today && to === today ? `${t("crmFilters.today")}, ${formatDay(today)}` : from && to ? from === to ? formatDay(from) : `${formatDay(from)} — ${formatDay(to)}` : from || to ? `${t(from ? "records.from" : "records.to")} ${formatDay(from || to)}` : t("records.periodAll");
  const openFilters = () => {
    setDraft(Object.fromEntries([...recordAdvancedKeys, "client", "attention"].map(key => [key, params.get(key) || ""])));
    setDialog("filters");
  };
  const total = summary ? recordWorkflows.reduce((sum, state) => sum + (summary[state] || 0), 0) : undefined;
  return <div className="min-w-0" data-testid="records-toolbar">
    <div className="flex min-w-0 items-center gap-2 overflow-x-auto px-1 py-1" data-testid="records-toolbar-row">
      <RecordsSearch params={params} setParams={setParams} />
      <Button ref={periodTrigger} variant="secondary" className="h-11 max-w-60 shrink-0 gap-2 lg:h-10" title={period} aria-label={`${t("analyticsWorkspace.period")}: ${period}`} aria-expanded={periodOpen} aria-controls={periodOpen ? "records-period-panel" : undefined} data-focus-return-id="records-period" onClick={() => setPeriodOpen(current => !current)}><CalendarDays size={16} className="shrink-0" /><span className="truncate">{period}</span></Button>
      <div className="w-48 shrink-0"><Select portal aria-label={t("records.pipeline")} density="compact" className="h-11 lg:h-10" value={filters.workflow || ""} onChange={event => update({ workflow: event.target.value })} options={[
        { value: "", label: `${t("crmFilters.allStatuses")}${total !== undefined ? ` · ${total}` : ""}` },
        ...recordWorkflows.map(state => ({ value: state, label: `${t(`records.${state}`)}${summary ? ` · ${summary[state] ?? 0}` : ""}` })),
      ]} /></div>
      <Button variant="secondary" className="h-11 shrink-0 gap-2 lg:h-10" title={chips.map(chip => `${chip.label}: ${chip.value}`).join("; ") || undefined} aria-haspopup="dialog" data-focus-return-id="records-filters" onClick={openFilters}><SlidersHorizontal size={16} />{t("crmFilters.filters")}{chips.length ? ` (${chips.length})` : ""}</Button>
      <Button variant="secondary" size="icon" className="h-11 w-11 shrink-0 lg:h-10 lg:w-10" aria-label={`${t("records.ordering")}: ${t(filters.ordering === "start_at" ? "records.ascending" : "records.descending")}`} title={t(filters.ordering === "start_at" ? "records.ascending" : "records.descending")} onClick={() => update({ ordering: filters.ordering === "start_at" ? "-start_at" : "start_at" })}>{filters.ordering === "start_at" ? <ArrowDownWideNarrow size={18} /> : <ArrowUpWideNarrow size={18} />}</Button>
      {hasFilters ? <Button variant="ghost" size="icon" className="h-11 w-11 shrink-0 lg:h-10 lg:w-10" aria-label={t("records.reset")} title={t("records.reset")} onClick={reset}><X size={16} /></Button> : null}
      <nav className="ml-auto flex shrink-0 items-center gap-1 whitespace-nowrap">
        <Link className="platforma-focus-ring rounded px-3 py-2 text-sm text-brand-700" to={`/app/calendar?date=${from || today}`}>{t("nav.calendar")}</Link>
        <Link className="platforma-focus-ring rounded px-3 py-2 text-sm text-brand-700" to="/app/appointments?view=plans">{t("plans.title")}</Link>
      </nav>
    </div>
    {periodOpen && <RecordsPeriodPanel from={from} to={to} today={today} onClose={closePeriod} onApply={range => { update(range); closePeriod(); }} />}
    <Modal open={dialog !== null} title={t("crmFilters.filters")} onClose={() => setDialog(null)} size="sm" focusReturnId={`records-${dialog}`}>
      <form className="space-y-4" onSubmit={event => { event.preventDefault(); update(draft); setDialog(null); }}>
        {dialog === "filters" ? chips.filter(chip => ["client", "attention"].includes(chip.key) && draft[chip.key]).map(chip => <Button key={chip.key} type="button" variant="secondary" aria-label={`${t("crmFilters.remove")}: ${chip.label}`} onClick={() => setDraft(current => ({ ...current, [chip.key]: "" }))}>{chip.label} {chip.value}<X size={14} /></Button>) : null}
        {fields.filter(field => field.key !== "branch" || branches.length || params.has("branch")).map(field => <Select key={field.key} label={field.label} value={draft[field.key] || ""} options={[{ value: "", label: t("records.all") }, ...field.options]} onChange={event => setDraft(current => ({ ...current, [field.key]: event.target.value }))} />)}
        <div className="sticky bottom-0 flex flex-wrap items-center justify-between gap-2 border-t border-platforma-border bg-surface-warm pt-3">
          {dialog === "filters" ? <Button type="button" variant="ghost" onClick={() => setDraft(Object.fromEntries([...recordAdvancedKeys, "client", "attention"].map(key => [key, ""])))}>{t("common.reset")}</Button> : null}
          <div className="ml-auto flex gap-2"><Button type="button" variant="secondary" onClick={() => setDialog(null)}>{t("common.cancel")}</Button><Button type="submit">{t("crmFilters.apply")}</Button></div>
        </div>
      </form>
    </Modal>
  </div>;
}

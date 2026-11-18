import { ArrowDownWideNarrow, ArrowUpWideNarrow, CalendarDays, SlidersHorizontal, X } from "lucide-react";
import { useRef, useState, type Dispatch, type SetStateAction } from "react";
import { useNavigate, type SetURLSearchParams } from "react-router";
import { Button } from "../../components/ui/Button";
import { RecordsPeriodPanel } from "./RecordsPeriodPanel";
import { RecordsSearch } from "./RecordsSearch";
import { CalendarPopover } from "../../components/ui/CalendarPopover";
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
  periodOpen: boolean;
  setPeriodOpen: Dispatch<SetStateAction<boolean>>;
  calendarOnly?: boolean;
};

export function RecordsToolbar({ today, params, setParams, filters, summary, resources, branches, members, periodOpen, setPeriodOpen, calendarOnly = false }: Props) {
  const { t, language } = useI18n();
  const navigate = useNavigate();
  const filterTrigger = useRef<HTMLButtonElement>(null);
  const closeFilters = (restoreFocus = true) => { setDialog(null); if (restoreFocus) filterTrigger.current?.focus({ preventScroll: true }); };
  const [dialog, setDialog] = useState<"filters" | null>(null);
  const periodTrigger = useRef<HTMLButtonElement>(null);
  const closePeriod = (restoreFocus = true) => { setPeriodOpen(false); if (restoreFocus) periodTrigger.current?.focus({ preventScroll: true }); };
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [resetAll, setResetAll] = useState(false);
  const update = (patch: Record<string, string>) => setParams(current => patchRecordFilters(current, patch));
  const fields = [
    { key: "resource", label: t("records.specialist"), options: resources },
    { key: "responsible_user", label: t("appointment.responsible"), options: members },
    { key: "confirmed", label: t("records.confirmation"), options: [{ value: "true", label: t("appointments.confirmed") }, { value: "false", label: t("records.unconfirmed") }] },
    { key: "branch", label: t("records.branch"), options: branches },
  ];
  const chips = fields.filter(field => params.get(field.key)).map(field => ({ key: field.key, label: field.label, value: field.options.find(option => String(option.value) === params.get(field.key))?.label || `#${params.get(field.key)}` }));
  if (filters.client) chips.push({ key: "client", label: t("appointment.client"), value: `#${filters.client}` });
  if (filters.attention) chips.push({ key: "attention", label: t("records.pendingResult"), value: "" });
  const from = filters.start_from || "";
  const to = params.get("to") || from;
  if (calendarOnly) return <div className="flex justify-end" data-testid="records-toolbar">
    <Button onClick={() => navigate(`/app/calendar?date=${from || today}`)}><CalendarDays size={16} />{t("nav.calendar")}</Button>
  </div>;
  const formatDay = (day: string) => {
    const date = new Date(`${day}T12:00:00Z`);
    return Number.isFinite(date.getTime()) ? new Intl.DateTimeFormat(language === "kk" ? "kk-KZ" : language === "en" ? "en-GB" : "ru-RU", { day: "numeric", month: language === "kk" ? "numeric" : "short", year: "numeric", timeZone: "UTC" }).format(date) : day;
  };
  const period = from === today && to === today ? `${t("crmFilters.today")}, ${formatDay(today)}` : from && to ? from === to ? formatDay(from) : `${formatDay(from)} — ${formatDay(to)}` : from || to ? `${t(from ? "records.from" : "records.to")} ${formatDay(from || to)}` : t("records.periodAll");
  const openFilters = () => {
    setPeriodOpen(false);
    setResetAll(false);
    setDraft(Object.fromEntries([...recordAdvancedKeys, "client", "attention"].map(key => [key, params.get(key) || ""])));
    setDialog("filters");
  };
  const total = summary ? recordWorkflows.reduce((sum, state) => sum + (summary[state] || 0), 0) : undefined;
  return <div className="min-w-0" data-testid="records-toolbar">
    <div className="flex min-w-0 flex-wrap items-center gap-2 px-1 lg:flex-nowrap lg:overflow-x-auto" data-testid="records-toolbar-row">
      <RecordsSearch params={params} setParams={setParams} />
      <Button ref={periodTrigger} data-calendar-trigger variant="secondary" className="h-11 max-w-60 shrink-0 gap-2 lg:h-10" title={period} aria-label={`${t("analyticsWorkspace.period")}: ${period}`} aria-expanded={periodOpen} aria-controls={periodOpen ? "records-period-panel" : undefined} data-focus-return-id="records-period" onClick={() => setPeriodOpen(current => !current)}><CalendarDays size={16} className="shrink-0" /><span className="truncate">{period}</span></Button>
      <div className="w-48 shrink-0"><Select portal aria-label={t("records.pipeline")} density="compact" className="h-11 lg:h-10" value={filters.workflow || ""} onChange={event => update({ workflow: event.target.value })} options={[
        { value: "", label: `${t("crmFilters.allStatuses")}${total !== undefined ? ` · ${total}` : ""}` },
        ...recordWorkflows.map(state => ({ value: state, label: `${t(`records.${state}`)}${summary ? ` · ${summary[state] ?? 0}` : ""}` })),
      ]} /></div>
      <Button ref={filterTrigger} variant="secondary" className="h-11 shrink-0 gap-2 lg:h-10" title={chips.map(chip => `${chip.label}: ${chip.value}`).join("; ") || undefined} aria-haspopup="dialog" aria-expanded={dialog !== null} aria-controls={dialog ? "records-filter-panel" : undefined} data-focus-return-id="records-filters" onClick={() => dialog ? closeFilters() : openFilters()}><SlidersHorizontal size={16} />{t("crmFilters.filters")}{chips.length ? ` (${chips.length})` : ""}</Button>
      <Button variant="secondary" size="icon" className="h-11 w-11 shrink-0 lg:h-10 lg:w-10" aria-label={`${t("records.ordering")}: ${t(filters.ordering === "start_at" ? "records.ascending" : "records.descending")}`} title={t(filters.ordering === "start_at" ? "records.ascending" : "records.descending")} onClick={() => update({ ordering: filters.ordering === "start_at" ? "-start_at" : "start_at" })}>{filters.ordering === "start_at" ? <ArrowDownWideNarrow size={18} /> : <ArrowUpWideNarrow size={18} />}</Button>
      <nav className="ml-auto flex shrink-0 items-center gap-1 whitespace-nowrap">
        <Button onClick={() => navigate(`/app/calendar?date=${from || today}`)}><CalendarDays size={16} />{t("nav.calendar")}</Button>
      </nav>
    </div>
    {periodOpen && <RecordsPeriodPanel anchor={periodTrigger} from={from} to={to} today={today} onClose={closePeriod} onApply={range => { update(range); closePeriod(); }} />}
    {dialog && <CalendarPopover anchor={filterTrigger} id="records-filter-panel" label={t("crmFilters.filters")} onClose={closeFilters}>
      <form className="space-y-4" onSubmit={event => { event.preventDefault(); setParams(current => patchRecordFilters(resetAll ? resetRecordFilters(current, today) : current, draft)); closeFilters(); }}>
        {dialog === "filters" ? chips.filter(chip => ["client", "attention"].includes(chip.key) && draft[chip.key]).map(chip => <Button key={chip.key} type="button" variant="secondary" aria-label={`${t("crmFilters.remove")}: ${chip.label}`} onClick={() => setDraft(current => ({ ...current, [chip.key]: "" }))}>{chip.label} {chip.value}<X size={14} /></Button>) : null}
        {fields.filter(field => field.key !== "branch" || branches.length || params.has("branch")).map(field => {
          const value = draft[field.key] || "";
          const unknown = value && !field.options.some(option => String(option.value) === value);
          return <Select portal key={field.key} label={field.label} value={value}
            options={[{ value: "", label: t("records.all") }, ...field.options, ...(unknown ? [{ value, label: `#${value}` }] : [])]}
            onChange={event => setDraft(current => ({ ...current, [field.key]: event.target.value }))} />;
        })}
        <div className="sticky bottom-0 flex flex-wrap items-center justify-between gap-2 border-t border-platforma-border bg-surface-card pt-3">
          {dialog === "filters" ? <Button type="button" variant="ghost" onClick={() => { setResetAll(true); setDraft(Object.fromEntries([...recordAdvancedKeys, "client", "attention"].map(key => [key, ""]))); }}>{t("common.reset")}</Button> : null}
          <div className="ml-auto flex gap-2"><Button type="button" variant="secondary" onClick={() => closeFilters()}>{t("common.cancel")}</Button><Button type="submit">{t("crmFilters.apply")}</Button></div>
        </div>
      </form>
    </CalendarPopover>}
  </div>;
}

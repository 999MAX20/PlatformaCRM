import { ChevronLeft, ChevronRight, SlidersHorizontal } from "lucide-react";
import { useRef, useState } from "react";
import { Button } from "../../../components/ui/Button";
import { CalendarPopover } from "../../../components/ui/CalendarPopover";
import { Select } from "../../../components/ui/Select";
import { cn } from "../../../lib/cn";
import { CalendarPicker } from "./CalendarPicker";
import { formatCalendarPeriod } from "../calendarUtils";
import type { CalendarTranslate, CalendarViewMode, SearchableCalendarFilterOption } from "../calendarTypes";

export type CalendarFilters = { service: string; resource: string; status: string; branch: string };

export function CalendarToolbar({ date, viewMode, locale, todayValue, filters, serviceOptions,
  resourceOptions, branchOptions, isServicesLoading, isResourcesLoading, onDateChange,
  onViewModeChange, onShiftDate, onApplyFilters, t,
}: {
  date: string; viewMode: CalendarViewMode; locale: string; todayValue: string;
  filters: CalendarFilters;
  serviceOptions: SearchableCalendarFilterOption[];
  resourceOptions: SearchableCalendarFilterOption[];
  branchOptions: SearchableCalendarFilterOption[];
  isServicesLoading: boolean; isResourcesLoading: boolean;
  onDateChange: (value: string) => void;
  onViewModeChange: (value: CalendarViewMode) => void;
  onShiftDate: (direction: number) => void;
  onApplyFilters: (filters: CalendarFilters) => void;
  t: CalendarTranslate;
}) {
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [draft, setDraft] = useState(filters);
  const filterTrigger = useRef<HTMLButtonElement>(null);
  const close = (restoreFocus = true) => {
    setFiltersOpen(false);
    if (restoreFocus) filterTrigger.current?.focus({ preventScroll: true });
  };
  const filterCount = Object.values(filters).filter(Boolean).length;
  const fields = [
    { key: "resource", label: t("records.specialist"), options: resourceOptions, disabled: isResourcesLoading },
    ...(branchOptions.length > 1 || filters.branch ? [{ key: "branch", label: t("records.branch"), options: branchOptions }] : []),
    { key: "status", label: t("records.status"), options: ["created", "confirmed", "rescheduled", "completed", "cancelled", "no_show"].map(value => ({ value, label: t(`status.${value}`) })) },
    { key: "service", label: t("records.service"), options: serviceOptions, disabled: isServicesLoading },
  ];
  const previousLabel = viewMode === "year" ? "calendar.previousYear" : viewMode === "month" ? "calendar.previousMonth" : "calendar.previousWeek";
  const nextLabel = viewMode === "year" ? "calendar.nextYear" : viewMode === "month" ? "calendar.nextMonth" : "calendar.nextWeek";

  return <div className="platforma-calendar-toolbar sticky top-[var(--app-header-height)] z-40 mb-2 min-w-0 bg-surface py-1" data-testid="calendar-toolbar">
    <div className="flex min-w-0 flex-wrap items-center gap-2 px-1 py-1 lg:flex-nowrap lg:overflow-x-auto" data-testid="calendar-toolbar-row">
      <Button variant="secondary" size="icon" className="h-11 w-11 shrink-0" onClick={() => onShiftDate(-1)} aria-label={t(previousLabel)}><ChevronLeft size={18} /></Button>
      <CalendarPicker value={date} onChange={onDateChange} locale={locale} todayValue={todayValue} periodLabel={formatCalendarPeriod(date, locale, viewMode)} />
      <Button variant="secondary" size="icon" className="h-11 w-11 shrink-0" onClick={() => onShiftDate(1)} aria-label={t(nextLabel)}><ChevronRight size={18} /></Button>
      <Button variant="ghost" className="h-11 shrink-0 px-3" onClick={() => onDateChange(todayValue)}>{t("calendar.today")}</Button>
      <div className="ml-auto grid shrink-0 grid-cols-3 rounded-control border border-platforma-border bg-platforma-card" role="group" aria-label={t("calendar.viewMode")}>
        {(["week", "month", "year"] as const).map(mode => <button key={mode} type="button" data-testid={`calendar-view-${mode}`} aria-pressed={viewMode === mode}
          className={cn("platforma-focus-ring min-h-11 rounded-control px-3 text-sm font-semibold", viewMode === mode ? "bg-brand-600 text-white" : "text-platforma-text hover:bg-surface-hover")}
          onClick={() => onViewModeChange(mode)}>{t(mode === "year" ? "crmFilters.year" : `calendar.${mode}`)}</button>)}
      </div>
      <Button ref={filterTrigger} variant="secondary" className="h-11 shrink-0" aria-haspopup="dialog" aria-expanded={filtersOpen}
        aria-controls={filtersOpen ? "calendar-filter-panel" : undefined} data-testid="calendar-filters-trigger"
        onClick={() => { if (filtersOpen) close(); else { setDraft(filters); setFiltersOpen(true); } }}>
        <SlidersHorizontal size={17} />{t("calendar.filters")}{filterCount ? ` (${filterCount})` : ""}
      </Button>
    </div>
    {filtersOpen && <CalendarPopover anchor={filterTrigger} id="calendar-filter-panel" testId="calendar-filters" label={t("calendar.filters")} onClose={close}>
      <form className="space-y-4" onSubmit={event => { event.preventDefault(); onApplyFilters(draft); close(); }}>
        {fields.map(field => {
          const key = field.key as keyof CalendarFilters;
          const unknown = draft[key] && !field.options.some(option => option.value === draft[key]);
          return <Select portal key={key} label={field.label} value={draft[key]} disabled={field.disabled}
            options={[{ value: "", label: t("records.all") }, ...field.options, ...(unknown ? [{ value: draft[key], label: `#${draft[key]}` }] : [])]}
            onChange={event => setDraft(current => ({ ...current, [key]: event.target.value }))} />;
        })}
        <div className="sticky bottom-0 flex flex-wrap items-center justify-between gap-2 border-t border-platforma-border bg-surface-card pt-3">
          <Button type="button" variant="ghost" onClick={() => setDraft({ resource: "", branch: "", service: "", status: "" })}>{t("common.reset")}</Button>
          <div className="ml-auto flex gap-2"><Button type="button" variant="secondary" onClick={() => close()}>{t("common.cancel")}</Button><Button type="submit">{t("crmFilters.apply")}</Button></div>
        </div>
      </form>
    </CalendarPopover>}
  </div>;
}

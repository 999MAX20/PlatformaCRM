import { ChevronLeft, ChevronRight, Filter } from "lucide-react";
import { useState, type ReactNode } from "react";

import { Button } from "../../../components/ui/Button";
import { Modal } from "../../../components/ui/Modal";
import { cn } from "../../../lib/cn";
import { CalendarPicker } from "./CalendarPicker";
import { CalendarResourceFilters } from "./CalendarFilters";
import { formatCalendarPeriod } from "../calendarUtils";
import type { CalendarTranslate, CalendarViewMode, SearchableCalendarFilterOption } from "../calendarTypes";

export function CalendarToolbar({
  date,
  viewMode,
  locale,
  todayValue,
  serviceFilter,
  resourceFilter,
  statusFilter,
  serviceOptions,
  resourceOptions,
  isServicesLoading,
  isResourcesLoading,
  onDateChange,
  onViewModeChange,
  onShiftDate,
  onServiceChange,
  onResourceChange,
  onStatusChange,
  children,
  t,
}: {
  date: string;
  viewMode: CalendarViewMode;
  locale: string;
  todayValue: string;
  serviceFilter: string;
  resourceFilter: string;
  statusFilter: string;
  serviceOptions: SearchableCalendarFilterOption[];
  resourceOptions: SearchableCalendarFilterOption[];
  isServicesLoading: boolean;
  isResourcesLoading: boolean;
  onDateChange: (value: string) => void;
  onViewModeChange: (value: CalendarViewMode) => void;
  onShiftDate: (days: number) => void;
  onServiceChange: (value: string) => void;
  onResourceChange: (value: string) => void;
  onStatusChange: (value: string) => void;
  children?: ReactNode;
  t: CalendarTranslate;
}) {
  const [filtersOpen, setFiltersOpen] = useState(false);
  const filterCount = [serviceFilter, resourceFilter, statusFilter].filter(Boolean).length;
  const filterControls = (
    <CalendarResourceFilters
      serviceFilter={serviceFilter}
      resourceFilter={resourceFilter}
      statusFilter={statusFilter}
      serviceOptions={serviceOptions}
      resourceOptions={resourceOptions}
      isServicesLoading={isServicesLoading}
      isResourcesLoading={isResourcesLoading}
      onServiceChange={onServiceChange}
      onResourceChange={onResourceChange}
      onStatusChange={onStatusChange}
      t={t}
    />
  );

  return (
    <section className="mb-4 rounded-card border border-platforma-border bg-platforma-card p-3 shadow-xs">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <Button variant="secondary" size="icon" className="h-10 w-10 shrink-0" onClick={() => onShiftDate(-1)} aria-label={t(viewMode === "month" ? "calendar.previousMonth" : viewMode === "week" ? "calendar.previousWeek" : "calendar.previousDay")}>
            <ChevronLeft size={18} />
          </Button>
          <CalendarPicker
            value={date}
            onChange={onDateChange}
            locale={locale}
            todayValue={todayValue}
            periodLabel={formatCalendarPeriod(date, locale, viewMode)}
          />
          <Button variant="secondary" size="icon" className="h-10 w-10 shrink-0" onClick={() => onShiftDate(1)} aria-label={t(viewMode === "month" ? "calendar.nextMonth" : viewMode === "week" ? "calendar.nextWeek" : "calendar.nextDay")}>
            <ChevronRight size={18} />
          </Button>
          <Button variant="secondary" className="h-10 px-3" onClick={() => onDateChange(todayValue)}>
            {t("calendar.today")}
          </Button>
        </div>
          <div className="grid shrink-0 grid-cols-2 rounded-control border border-platforma-border bg-surface-muted p-1">
            {[
              { value: "week", label: t("calendar.week") },
              { value: "month", label: t("calendar.month") },
            ].map((item) => (
              <button
                key={item.value}
                type="button"
                data-testid={`calendar-view-${item.value}`}
                aria-pressed={viewMode === item.value}
                className={cn(
                  "rounded-control px-3 py-2 text-xs font-bold transition sm:text-sm",
                  viewMode === item.value ? "bg-platforma-card text-brand-700 shadow-xs" : "text-platforma-muted hover:bg-surface-hover hover:text-platforma-text",
                )}
                onClick={() => onViewModeChange(item.value as CalendarViewMode)}
              >
                {item.label}
              </button>
            ))}
          </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-platforma-border pt-3">
        {children}
        <Button variant="secondary" aria-haspopup="dialog" aria-expanded={filtersOpen} onClick={() => setFiltersOpen(true)}><Filter size={17} />{t("calendar.filters")}{filterCount ? ` · ${filterCount}` : ""}</Button>
      </div>
      <Modal open={filtersOpen} onClose={() => setFiltersOpen(false)} title={t("calendar.filters")} size="sm" testId="calendar-filters">
        <div className="space-y-4">{filterControls}</div>
        <div className="mt-5 flex justify-end"><Button onClick={() => setFiltersOpen(false)}>{t("common.close")}</Button></div>
      </Modal>
    </section>
  );
}

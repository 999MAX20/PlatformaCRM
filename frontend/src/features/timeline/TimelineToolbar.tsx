import { CalendarDays, Search } from "lucide-react";
import { categoryConfig } from "../../components/crm/drawers/timelineHelpers";
import { Button } from "../../components/ui/Button";
import { DatePickerPanel, isCalendarDate, type DateRangeValue } from "../../components/ui/DateRangePicker";
import { dateInTimeZone } from "../../lib/format";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { useI18n } from "../../lib/i18n";
import type { Id } from "../../types";
import type { TimelineFilters } from "../../types/timeline";
import { TimelineActorFilter } from "./TimelineActorFilter";
import { useId, useRef, useState } from "react";

export function TimelineToolbar({
  businessId,
  filters,
  onChange,
  onReset,
  onDateChange,
  timeZone,
}: {
  businessId: Id;
  filters: TimelineFilters;
  onChange: (key: keyof TimelineFilters, value: string | number) => void;
  onReset: () => void;
  onDateChange: (range: DateRangeValue) => void;
  timeZone: string;
}) {
  const { t, language } = useI18n();
  const anchor = useRef<HTMLButtonElement>(null);
  const [calendarOpen, setCalendarOpen] = useState(false);
  const closeCalendar = (restore = true) => { setCalendarOpen(false); if (restore) anchor.current?.focus(); };
  const formatDate = (date: string) => isCalendarDate(date) ? new Intl.DateTimeFormat(language, { day: "numeric", month: "numeric", year: "numeric", timeZone: "UTC" }).format(new Date(`${date}T12:00:00Z`)) : date;
  const dateLabel = filters.date_from && filters.date_to ? `${formatDate(filters.date_from)} — ${formatDate(filters.date_to)}` : filters.date_from ? `${t("crmFilters.from")} ${formatDate(filters.date_from)}` : filters.date_to ? `${t("crmFilters.to")} ${formatDate(filters.date_to)}` : t("timeline.chooseDate");
  const [expanded, setExpanded] = useState(false);
  const filterId = useId();
  const filterCount = [filters.category, filters.actor, filters.date_from, filters.date_to].filter(Boolean).length;
  const active = Boolean(
    filters.entity_id || filters.entity_type || filters.search ||
      filters.category ||
      filters.actor ||
      filters.date_from ||
      filters.date_to,
  );
  return (
    <div
      className="shrink-0 space-y-3 border-b border-platforma-border p-3 [--global-search-width:100%] lg:grid lg:grid-cols-[minmax(100px,1fr)_minmax(120px,180px)_minmax(120px,180px)_auto_auto] lg:gap-2 lg:space-y-0"
      data-testid="timeline-toolbar"
    >
      {filters.entity_id ? <p className="col-span-full text-sm text-platforma-subtle">{t("timeline.object")} #{filters.entity_id}</p> : null}
      <div className="flex gap-2 lg:contents [&>label]:min-w-0 [&>label]:flex-1">
        <Input
          pageSearch aria-label={t("timeline.search")}
          placeholder={t("timeline.searchPlaceholder")}
          leftIcon={<Search size={18} />}
          type="search"
          maxLength={160}
          value={filters.search}
          onChange={(e) => onChange("search", e.target.value)}
        />
        <Button type="button" variant="secondary" className="lg:hidden" aria-expanded={expanded} aria-controls={filterId} onClick={() => setExpanded(value => !value)}>{t("timeline.filters")}{filterCount ? ` (${filterCount})` : ""}</Button>
      </div>
      <div id={filterId} className={`${expanded ? "block" : "hidden"} space-y-3 lg:contents`}>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:contents">
        <Select
          aria-label={t("timeline.category")}
          value={filters.category}
          options={[
            { value: "", label: t("timeline.allCategories") },
            ...Object.entries(categoryConfig).map(([value, config]) => ({
              value,
              label: t(config.labelKey),
            })),
          ]}
          onChange={(e) => onChange("category", e.target.value)}
        />
        <TimelineActorFilter
          businessId={businessId}
          value={filters.actor}
          onChange={(value) => onChange("actor", value)}
        />
      </div>
      <div className="flex flex-wrap items-center gap-2 lg:contents">
        <Button ref={anchor} data-calendar-trigger type="button" variant="secondary" className="min-h-11 min-w-0 max-w-full" aria-label={t("timeline.chooseDate")} aria-haspopup="dialog" aria-expanded={calendarOpen} onClick={() => setCalendarOpen(value => !value)}>
          <CalendarDays size={17} className="shrink-0" /><span className="truncate">{dateLabel}</span>
        </Button>
        {calendarOpen && <DatePickerPanel anchor={anchor} label={t("timeline.chooseDate")} value={{ from: filters.date_from, to: filters.date_to }} today={dateInTimeZone(new Date(), timeZone)} allowClear onApply={range => { onDateChange(range); closeCalendar(); }} onClose={closeCalendar} />}
        {active && (
          <Button type="button" variant="ghost" onClick={onReset}>
            {t("timeline.reset")}
          </Button>
        )}
      </div>
      </div>
      {!expanded && active && <Button type="button" variant="ghost" className="lg:hidden" onClick={onReset}>{t("timeline.reset")}</Button>}
    </div>
  );
}

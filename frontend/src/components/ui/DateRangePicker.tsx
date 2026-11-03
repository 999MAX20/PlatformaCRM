import { CalendarDays, ChevronLeft, ChevronRight, X } from "lucide-react";
import { useId, useRef, useState, type RefObject } from "react";
import { useI18n } from "../../lib/i18n";
import { cn } from "../../lib/cn";
import { Button } from "./Button";
import { Select } from "./Select";
import { CalendarPopover } from "./CalendarPopover";

export type DateRangeValue = { from: string; to: string };
const asDate = (value: string) => new Date(`${value}T12:00:00Z`);
const keyOf = (value: Date) => value.toISOString().slice(0, 10);
export function isCalendarDate(value: string) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = asDate(value);
  return Number.isFinite(date.getTime()) && keyOf(date) === value;
}
function shift(value: string, days: number) {
  const date = asDate(value);
  date.setUTCDate(date.getUTCDate() + days);
  return keyOf(date);
}

/** Date-only control. API boundaries are resolved in the business timezone, not the browser's. */
export function DateRangePicker({ label, value, onChange, today, range = true, inline = false, allowClear = true, compact = true, showHint = false, showPresets = false, min, max }: {
  label: string;
  value: DateRangeValue;
  onChange: (value: DateRangeValue) => void;
  today: string;
  range?: boolean;
  inline?: boolean;
  allowClear?: boolean;
  compact?: boolean;
  showHint?: boolean;
  showPresets?: boolean;
  min?: string;
  max?: string;
}) {
  const { t, language } = useI18n();
  const locale = language === "kk" ? "kk-KZ" : language === "en" ? "en-GB" : "ru-RU";
  const selectedDay = isCalendarDate(value.from) ? value.from : isCalendarDate(value.to) ? value.to : today;
  const initialDay = min && selectedDay < min ? min : max && selectedDay > max ? max : selectedDay;
  const trigger = useRef<HTMLButtonElement>(null);
  const grid = useRef<HTMLDivElement>(null);
  const id = useId();
  const [open, setOpen] = useState(false);
  const [month, setMonth] = useState(initialDay.slice(0, 7));
  const [focusDay, setFocusDay] = useState(initialDay);
  const [choosingEnd, setChoosingEnd] = useState(false);
  const format = (date: string) => !isCalendarDate(date) ? date : new Intl.DateTimeFormat(locale, { day: "numeric", month: language === "kk" ? "numeric" : "short", year: "numeric", timeZone: "UTC" }).format(asDate(date));
  const display = !range && value.from ? format(value.from) : value.from && value.to ? `${format(value.from)} — ${format(value.to)}`
    : value.from ? `${t("crmFilters.from")} ${format(value.from)}`
      : value.to ? `${t("crmFilters.to")} ${format(value.to)}` : t("crmFilters.anyDate");
  const first = asDate(`${month}-01`);
  const offset = (first.getUTCDay() + 6) % 7;
  const days = new Date(Date.UTC(first.getUTCFullYear(), first.getUTCMonth() + 1, 0)).getUTCDate();
  const cells = Array.from({ length: Math.ceil((offset + days) / 7) * 7 }, (_, index) => shift(`${month}-01`, index - offset));
  const year = first.getUTCFullYear();
  const years = Array.from({ length: Math.max(2100, year + 1) - Math.min(1900, year) + 1 }, (_, index) => Math.min(1900, year) + index);
  const months = Array.from({ length: 12 }, (_, index) => ({ value: String(index + 1).padStart(2, "0"), label: t(`calendar.month.${index + 1}`) }));
  function close() { setOpen(false); trigger.current?.focus(); }
  function moveMonth(delta: number) {
    const next = new Date(Date.UTC(year, first.getUTCMonth() + delta, 1));
    setMonth(keyOf(next).slice(0, 7));
    setFocusDay(keyOf(next));
  }
  function select(day: string) {
    if (!range) { onChange({ from: day, to: day }); close(); return; }
    if (!choosingEnd) { onChange({ from: day, to: "" }); setChoosingEnd(true); }
    else { onChange(day < value.from ? { from: day, to: value.from } : { from: value.from, to: day }); setChoosingEnd(false); close(); }
  }
  function focusDate(day: string) {
    day = min && day < min ? min : max && day > max ? max : day;
    setMonth(day.slice(0, 7)); setFocusDay(day);
    requestAnimationFrame(() => grid.current?.querySelector<HTMLButtonElement>(`[data-date="${day}"]`)?.focus());
  }
  if (!inline) return <div className="min-w-0 space-y-1.5">
    <span id={`${id}-label`} className="block text-sm font-medium text-platforma-text">{label}</span>
    <Button ref={trigger} data-calendar-trigger type="button" variant="secondary" aria-labelledby={`${id}-label ${id}-value`} aria-haspopup="dialog" aria-expanded={open} aria-controls={open ? id : undefined}
      className="min-h-11 w-full justify-between gap-2 text-left" onClick={() => setOpen(current => !current)}>
      <span id={`${id}-value`} className="min-w-0 whitespace-normal text-sm">{display}</span><CalendarDays size={17} className="shrink-0 text-platforma-subtle" />
    </Button>
    {open && <DatePickerPanel id={id} anchor={trigger} label={label} value={value} today={today} range={range} allowClear={allowClear} min={min} max={max}
      onApply={next => { onChange(next); close(); }} onClose={restore => { setOpen(false); if (restore !== false) trigger.current?.focus(); }} />}
  </div>;
  return <div className="min-w-0 space-y-1.5" onKeyDown={event => {
    if (event.key === "Escape" && event.defaultPrevented) { event.stopPropagation(); return; }
    if (event.key === "Escape" && !inline && open && !(event.target instanceof Element && event.target.closest('[role="combobox"][aria-expanded="true"]'))) {
      event.preventDefault(); event.stopPropagation(); close();
    }
  }}>
    {inline || open ? <div id={id} role="group" aria-label={label} className={cn("rounded-card", inline ? "bg-inherit" : "border border-platforma-border bg-surface-card p-3 shadow-card")}>
      <div className="mb-2 flex items-center gap-0 min-[360px]:gap-1">
        <Button type="button" size="icon" variant="ghost" className="h-11 w-11 shrink-0" aria-label={t("crmFilters.previousMonth")} onClick={() => moveMonth(-1)}><ChevronLeft size={17} /></Button>
        <div className="min-w-0 flex-1"><Select className={compact ? "gap-1! px-2!" : undefined} aria-label={t("crmFilters.month")} value={month.slice(5)} options={months} onChange={event => { setMonth(`${year}-${event.target.value}`); setFocusDay(`${year}-${event.target.value}-01`); }} /></div>
        <div className={cn("shrink-0", compact ? "w-18 min-[360px]:w-20" : "w-24")}><Select className={compact ? "gap-1! px-1! min-[360px]:px-2!" : undefined} aria-label={t("crmFilters.year")} value={year} options={years.map(item => ({ value: item, label: String(item) }))} onChange={event => { setMonth(`${event.target.value}-${month.slice(5)}`); setFocusDay(`${event.target.value}-${month.slice(5)}-01`); }} /></div>
        <Button type="button" size="icon" variant="ghost" className="h-11 w-11 shrink-0" aria-label={t("crmFilters.nextMonth")} onClick={() => moveMonth(1)}><ChevronRight size={17} /></Button>
      </div>
      {range && <p role="status" className={showHint ? "mb-2 text-xs text-platforma-subtle" : "sr-only"}>{t(choosingEnd ? "crmFilters.chooseEnd" : "crmFilters.chooseStart")}</p>}
      <div className="grid grid-cols-7 text-center text-xs text-platforma-muted">{["mon", "tue", "wed", "thu", "fri", "sat", "sun"].map(day => <span key={day} className="py-2">{t(`weekday.${day}Short`)}</span>)}</div>
      <div ref={grid} role="grid" aria-label={label} className="space-y-1">
        {Array.from({ length: cells.length / 7 }, (_, row) => <div key={row} role="row" className="grid grid-cols-7">{cells.slice(row * 7, row * 7 + 7).map(day => {
          const selected = day === value.from || day === value.to;
          const within = Boolean(value.from && value.to && day >= value.from && day <= value.to);
          const disabled = Boolean((min && day < min) || (max && day > max));
          return <button key={day} type="button" role="gridcell" data-date={day} tabIndex={day === focusDay ? 0 : -1} aria-label={format(day)} aria-selected={selected || within} aria-current={day === today ? "date" : undefined}
            disabled={disabled}
            className={cn("platforma-focus-ring relative h-11 min-w-0 rounded-control text-sm tabular-nums transition disabled:cursor-not-allowed disabled:text-disabled-content disabled:bg-disabled-surface", !selected && "hover:bg-surface-hover", day.slice(0, 7) !== month && "text-platforma-muted", within && "bg-brand-50", selected && "bg-brand-600 font-semibold text-white hover:bg-brand-700", !selected && day === today && "font-bold ring-1 ring-inset ring-brand-500")}
            onClick={() => { setFocusDay(day); select(day); }} onKeyDown={event => {
              const delta = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 }[event.key];
              if (delta !== undefined) { event.preventDefault(); focusDate(shift(day, delta)); }
              if (event.key === "Home" || event.key === "End") { event.preventDefault(); const weekday = (asDate(day).getUTCDay() + 6) % 7; focusDate(shift(day, event.key === "Home" ? -weekday : 6 - weekday)); }
              if (event.key === "PageUp" || event.key === "PageDown") { event.preventDefault(); const date = asDate(day); focusDate(keyOf(new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + (event.key === "PageUp" ? -1 : 1), 1)))); }
            }}>{asDate(day).getUTCDate()}</button>;
        })}</div>)}
      </div>
      {(showPresets || (range && allowClear)) && <div className="mt-3 flex flex-wrap items-center gap-1 border-t border-platforma-border pt-2">
        {showPresets && (range ? [1, 7, 30] : [1]).map(count => <Button key={count} type="button" size="sm" variant="ghost" onClick={() => { onChange({ from: shift(today, 1 - count), to: today }); close(); }}>{t(count === 1 ? "crmFilters.today" : count === 7 ? "crmFilters.last7" : "crmFilters.last30")}</Button>)}
        {range && allowClear && <Button type="button" size="sm" variant="ghost" onClick={() => { onChange({ from: "", to: "" }); setChoosingEnd(false); close(); }}><X size={14} />{t("common.clear")}</Button>}
      </div>}
    </div> : null}
  </div>;
}

export function DatePickerPanel({ anchor, label, value, today, onApply, onClose, range = true, allowClear = false, validate, min, max, id, testId }: {
  anchor: RefObject<HTMLElement | null>; label: string; value: DateRangeValue; today: string;
  onApply: (value: DateRangeValue) => void; onClose: (restoreFocus?: boolean) => void;
  range?: boolean; allowClear?: boolean; validate?: (value: DateRangeValue) => boolean;
  min?: string; max?: string; id?: string; testId?: string;
}) {
  const { t } = useI18n();
  const [draft, setDraft] = useState(value);
  const empty = !draft.from && !draft.to;
  const valid = ((allowClear && empty) || (isCalendarDate(draft.from) && isCalendarDate(draft.to) && draft.from <= draft.to
    && (!min || draft.from >= min) && (!max || draft.to <= max))) && (!validate || validate(draft));
  return <CalendarPopover anchor={anchor} label={label} id={id} testId={testId} onClose={onClose}>
    <DateRangePicker inline compact range={range} allowClear={false} label={label} value={draft} today={today} min={min} max={max}
      onChange={next => { setDraft(next); if (!range) onApply(next); }} />
    <div className="mt-3 flex flex-wrap justify-end gap-2 border-t border-platforma-border pt-3">
      {allowClear && <Button type="button" variant="ghost" className="mr-auto min-h-11" onClick={() => range ? setDraft({ from: "", to: "" }) : onApply({ from: "", to: "" })}>{t("common.clear")}</Button>}
      <Button type="button" variant="secondary" className="min-h-11" onClick={() => onClose()}>{t("common.cancel")}</Button>
      {range && <Button type="button" className="min-h-11" disabled={!valid} onClick={() => { if (valid) onApply(draft); }}>{t("crmFilters.apply")}</Button>}
    </div>
  </CalendarPopover>;
}

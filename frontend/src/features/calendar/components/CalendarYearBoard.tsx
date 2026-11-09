import { useEffect, useRef, useState } from "react";
import { cn } from "../../../lib/cn";
import { formatPickerDate, getMonthDates, shiftDateValue, toDateInputValue } from "../calendarUtils";
import type { CalendarTranslate } from "../calendarTypes";

export function CalendarYearBoard({ date, periodDate = date, today, locale, loading, days, onSelectDay, onOpenMonth, onNavigate, t }: {
  date: string; today: string; locale: string; loading: boolean;
  periodDate?: string;
  days: { date: string; appointments: number }[];
  onSelectDay: (date: string) => void;
  onOpenMonth: (date: string) => void;
  onNavigate: (date: string) => void;
  t: CalendarTranslate;
}) {
  const year = Number(periodDate.slice(0, 4));
  const counts = new Map(days.map(day => [day.date, day.appointments]));
  const grid = useRef<HTMLDivElement>(null);
  const [focusDay, setFocusDay] = useState(date);
  const pendingFocus = useRef<string | null>(null);
  useEffect(() => {
    if (pendingFocus.current) {
      grid.current?.querySelector<HTMLButtonElement>(`[data-calendar-day="${pendingFocus.current}"]`)?.focus();
      pendingFocus.current = null;
    }
  }, [year]);
  function moveFocus(day: string) {
    const target = grid.current?.querySelector<HTMLButtonElement>(`[data-calendar-day="${day}"]`);
    if (target) target.focus();
    else { pendingFocus.current = day; onNavigate(day); }
  }
  const tabDay = focusDay.startsWith(`${year}-`) ? focusDay : date.startsWith(`${year}-`) ? date : periodDate;
  return <div ref={grid} data-testid="calendar-board-year" aria-busy={loading}
    className="grid grid-cols-1 gap-3 min-[760px]:grid-cols-2 min-[1120px]:grid-cols-3 min-[1500px]:grid-cols-4">
    {Array.from({ length: 12 }, (_, index) => {
      const month = `${year}-${String(index + 1).padStart(2, "0")}`;
      const monthLabel = new Intl.DateTimeFormat(locale, { month: "long" }).format(new Date(year, index, 1));
      const cells = getMonthDates(`${month}-01`);
      const total = days.filter(day => day.date.startsWith(month)).reduce((sum, day) => sum + day.appointments, 0);
      return <section key={month} className="min-w-0 rounded-card border border-platforma-border bg-platforma-card p-2" data-calendar-month={month}>
        <button type="button" className="platforma-focus-ring mb-1 flex min-h-11 w-full items-center justify-between gap-2 rounded-control px-2 text-left hover:bg-surface-hover"
          aria-label={t("calendar.openMonth", { month: `${monthLabel} ${year}` })} onClick={() => onOpenMonth(`${month}-01`)}>
          <span className="font-semibold capitalize">{monthLabel}</span>
          {!loading && total > 0 && <span className="text-xs text-platforma-muted">{t("calendar.appointmentCount", { count: total })}</span>}
        </button>
        <div className="grid grid-cols-7 text-center text-xs text-platforma-muted">
          {cells.slice(0, 7).map(day => <span key={day.getDay()} className="py-1">{new Intl.DateTimeFormat(locale, { weekday: "short" }).format(day)}</span>)}
        </div>
        <div className="grid grid-cols-7 gap-y-0.5">
          {cells.map(cell => {
            const day = toDateInputValue(cell);
            if (!day.startsWith(month)) return <span key={day} aria-hidden="true" />;
            const count = counts.get(day) || 0;
            return <button type="button" key={day} data-calendar-day={day} data-focus-return-id={`calendar-day-${day}`} tabIndex={day === tabDay ? 0 : -1}
              aria-label={`${formatPickerDate(day, locale)}. ${loading ? t("common.loadingData") : t("calendar.appointmentCount", { count })}`}
              aria-pressed={day === date} aria-current={day === today ? "date" : undefined}
              className={cn("platforma-focus-ring flex min-h-11 min-w-0 flex-col items-center justify-center rounded-control text-sm tabular-nums hover:bg-surface-hover",
                !loading && count > 0 && "bg-brand-50 text-brand-950", day === date && "ring-1 ring-inset ring-brand-500")}
              onFocus={() => setFocusDay(day)} onClick={() => onSelectDay(day)}
              onKeyDown={event => {
                const delta = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 }[event.key];
                if (delta !== undefined) { event.preventDefault(); moveFocus(shiftDateValue(day, delta)); }
                if (event.key === "Home" || event.key === "End") { event.preventDefault(); const weekday = (cell.getDay() + 6) % 7; moveFocus(shiftDateValue(day, event.key === "Home" ? -weekday : 6 - weekday)); }
              }}>
              <span className={cn("inline-flex h-6 min-w-6 items-center justify-center rounded-full", day === today && "bg-brand-600 font-semibold text-white")}>{cell.getDate()}</span>
              {!loading && count > 0 && <span aria-hidden="true" className="max-w-full truncate px-0.5 text-[10px] leading-3 font-semibold">{count}</span>}
            </button>;
          })}
        </div>
      </section>;
    })}
  </div>;
}

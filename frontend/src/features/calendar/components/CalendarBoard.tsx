import { useEffect, useMemo, useRef, useState } from "react";
import { ListTodo } from "lucide-react";
import { cn } from "../../../lib/cn";
import { dateInTimeZone } from "../../../lib/format";
import type { Appointment, Task } from "../../../types";
import type { CalendarTranslate, CalendarViewMode } from "../calendarTypes";
import { formatPickerDate, formatTime, getMonthDates, getWeekDates, shiftDateValue, toDateInputValue } from "../calendarUtils";

type Entry = { key: string; at: string; title: string; detail?: string; kind: "appointment" | "task" };

export function CalendarBoard({ loading, canViewTasks, date, periodDate = date, viewMode, today, locale, timeZone, appointments, tasks, onSelectDay, onNavigate, t }: {
  loading: boolean; canViewTasks: boolean;
  date: string; viewMode: Exclude<CalendarViewMode, "year">; today: string; locale: string; timeZone: string;
  periodDate?: string;
  appointments: Appointment[]; tasks: Task[];
  onSelectDay: (date: string) => void; onNavigate: (date: string) => void; t: CalendarTranslate;
}) {
  const grid = useRef<HTMLDivElement>(null);
  const [focusDay, setFocusDay] = useState(date);
  const pendingFocus = useRef<string | null>(null);
  useEffect(() => {
    if (pendingFocus.current) {
      grid.current?.querySelector<HTMLButtonElement>(`[data-calendar-day="${pendingFocus.current}"]`)?.focus();
      pendingFocus.current = null;
    }
  }, [date, periodDate, viewMode]);
  const entries = useMemo(() => {
    const days = new Map<string, Entry[]>();
    function add(entry: Entry) {
      const key = dateInTimeZone(entry.at, timeZone);
      days.set(key, [...(days.get(key) || []), entry]);
    }
    appointments.forEach(item => add({ key: `appointment-${item.id}`, at: item.start_at, title: item.client_name || t("common.client"), detail: item.service_name, kind: "appointment" }));
    if (canViewTasks) tasks.forEach(item => { if (item.due_at && !item.is_archived && !["done", "cancelled"].includes(item.status)) add({ key: `task-${item.id}`, at: item.due_at, title: item.title, kind: "task" }); });
    for (const rows of days.values()) rows.sort((a, b) => Date.parse(a.at) - Date.parse(b.at) || a.key.localeCompare(b.key));
    return days;
  }, [appointments, tasks, timeZone, t, canViewTasks]);
  function moveFocus(day: string) {
    const target = grid.current?.querySelector<HTMLButtonElement>(`[data-calendar-day="${day}"]`);
    if (target) { target.focus(); return; }
    pendingFocus.current = day;
    onNavigate(day);
  }
  const cells = viewMode === "month" ? getMonthDates(periodDate) : getWeekDates(periodDate);
  const week = getWeekDates(periodDate);
  const tabDay = cells.some(cell => toDateInputValue(cell) === focusDay) ? focusDay : cells.some(cell => toDateInputValue(cell) === date) ? date : periodDate;
  return <>
    <div ref={grid} aria-busy={loading} data-testid={`calendar-board-${viewMode}`} className="overflow-hidden rounded-card border border-platforma-border bg-platforma-card shadow-xs">
      <div className={cn("grid grid-cols-7 border-b border-platforma-border bg-surface-muted", viewMode === "week" && "hidden md:grid")}>
        {week.map(day => <div key={day.getDay()} className="py-2 text-center text-xs font-semibold text-platforma-muted">{new Intl.DateTimeFormat(locale, { weekday: "short" }).format(day)}</div>)}
      </div>
      <div className={cn("grid gap-px bg-platforma-border", viewMode === "month" ? "grid-cols-7" : "grid-cols-1 md:grid-cols-7")}>
        {cells.map(cell => {
          const day = toDateInputValue(cell);
          const rows = entries.get(day) || [];
          const records = rows.filter(row => row.kind === "appointment");
          const count = records.length;
          const taskCount = rows.length - count;
          const previewLimit = viewMode === "week" ? 5 : 2;
          const outsideMonth = viewMode === "month" && day.slice(0, 7) !== periodDate.slice(0, 7);
          return <button key={day} type="button" data-calendar-day={day} data-focus-return-id={`calendar-day-${day}`}
            aria-label={`${formatPickerDate(day, locale)}. ${loading ? t("common.loadingData") : `${t("calendar.bookings")}: ${count}${canViewTasks ? `. ${t("calendar.tasksToday")}: ${taskCount}` : ""}`}`}
            aria-pressed={day === date} aria-current={day === today ? "date" : undefined}
            tabIndex={day === tabDay ? 0 : -1} onFocus={() => setFocusDay(day)}
            className={cn("platforma-focus-ring group flex min-w-0 cursor-pointer flex-col items-stretch justify-start p-1 text-left transition hover:bg-surface-hover sm:p-1.5", outsideMonth ? "bg-surface-muted text-platforma-muted" : "bg-platforma-card", viewMode === "month" ? "h-20 sm:h-[120px]" : "min-h-28 md:min-h-44", day === date && "bg-brand-50/50 ring-1 ring-inset ring-brand-400")}
            onClick={() => onSelectDay(day)}
            onKeyDown={event => {
              const delta = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 }[event.key];
              if (delta !== undefined) { event.preventDefault(); moveFocus(shiftDateValue(day, delta)); }
              if (event.key === "Home" || event.key === "End") { event.preventDefault(); const weekday = (cell.getDay() + 6) % 7; moveFocus(shiftDateValue(day, event.key === "Home" ? -weekday : 6 - weekday)); }
            }}>
            <span className="mb-1 flex items-center gap-1">
              <span className={cn("inline-flex h-6 min-w-6 items-center justify-center rounded-full text-sm font-semibold tabular-nums", day === today ? "bg-brand-600 text-white" : outsideMonth ? "text-platforma-muted" : "text-platforma-text")}>{cell.getDate()}</span>
              {viewMode === "week" && <span className="text-xs text-platforma-muted md:hidden">{new Intl.DateTimeFormat(locale, { weekday: "long", month: "short" }).format(cell)}</span>}
              {!loading && count > 0 && <span className="ml-auto hidden min-w-0 truncate text-xs tabular-nums text-platforma-muted sm:block">{t("calendar.appointmentCount", { count })}</span>}
            </span>
            {!loading && <span aria-hidden="true" className="block space-y-0.5">
              {count > 0 && viewMode === "month" && <span className="block rounded bg-brand-50 px-1 text-center text-xs font-semibold text-brand-950 sm:hidden">{count}</span>}
              {records.slice(0, previewLimit).map(row => <span key={row.key} className={cn("overflow-hidden rounded bg-brand-50 px-1 py-0.5 text-xs leading-4 text-brand-950", viewMode === "month" ? "hidden sm:block" : "block")}>
                <span className="block truncate"><span className="font-semibold tabular-nums">{formatTime(row.at, locale, timeZone)}</span><span className="ml-1">{row.title}</span></span>
                {viewMode === "week" && row.detail && <span className="block truncate text-platforma-muted">{row.detail}</span>}
              </span>)}
              {count > previewLimit && <span className={cn("px-1 text-xs font-semibold text-brand-700", viewMode === "month" ? "hidden sm:block" : "block")}>{t("calendar.moreEntries", { count: count - previewLimit })}</span>}
            </span>}
            {!loading && taskCount > 0 && <span className="mt-auto block truncate text-xs text-platforma-muted"><span className="hidden sm:inline">{t("calendar.taskCount", { count: taskCount })}</span><span aria-hidden="true" className="flex items-center justify-center gap-0.5 sm:hidden"><ListTodo size={12} />{taskCount}</span></span>}
          </button>;
        })}
      </div>
    </div>
  </>;
}

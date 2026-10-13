import { useEffect, useId, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { cn } from "../../../lib/cn";
import { dateInTimeZone } from "../../../lib/format";
import type { Appointment, Task } from "../../../types";
import type { CalendarTranslate, CalendarViewMode } from "../calendarTypes";
import { formatPickerDate, formatTime, getMonthDates, getWeekDates, shiftDateValue, toDateInputValue } from "../calendarUtils";

type Entry = { key: string; at: string; title: string; detail?: string; kind: "appointment" | "task" };

export function CalendarBoard({ loading, canViewTasks, date, viewMode, today, locale, timeZone, appointments, tasks, onSelectDay, onNavigate, t }: {
  loading: boolean; canViewTasks: boolean;
  date: string; viewMode: CalendarViewMode; today: string; locale: string; timeZone: string;
  appointments: Appointment[]; tasks: Task[];
  onSelectDay: (date: string) => void; onNavigate: (date: string) => void; t: CalendarTranslate;
}) {
  const grid = useRef<HTMLDivElement>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const id = useId();
  const [preview, setPreview] = useState<{ date: string; left: number; top: number } | null>(null);
  const entries = useMemo(() => {
    const days = new Map<string, Entry[]>();
    function add(entry: Entry) {
      const key = dateInTimeZone(entry.at, timeZone);
      days.set(key, [...(days.get(key) || []), entry]);
    }
    appointments.forEach(item => add({ key: `appointment-${item.id}`, at: item.start_at, title: item.client_name || t("common.client"), detail: item.service_name, kind: "appointment" }));
    tasks.forEach(item => { if (item.due_at && !item.is_archived && !["done", "cancelled"].includes(item.status)) add({ key: `task-${item.id}`, at: item.due_at, title: item.title, kind: "task" }); });
    for (const rows of days.values()) rows.sort((a, b) => Date.parse(a.at) - Date.parse(b.at) || a.key.localeCompare(b.key));
    return days;
  }, [appointments, tasks, timeZone, t]);
  function cancelTimer() { if (timer.current) clearTimeout(timer.current); }
  function dismiss() { cancelTimer(); setPreview(null); }
  function show(day: string, element: HTMLElement) {
    cancelTimer();
    if (loading) return;
    const rect = element.getBoundingClientRect();
    timer.current = setTimeout(() => setPreview({ date: day, left: Math.max(8, Math.min(rect.left, window.innerWidth - 336)), top: Math.max(8, Math.min(rect.bottom + 6, window.innerHeight - 350)) }), 300);
  }
  function deferHide() { cancelTimer(); timer.current = setTimeout(() => setPreview(null), 160); }
  useEffect(() => {
    const close = () => { if (timer.current) clearTimeout(timer.current); setPreview(null); };
    const escape = (event: KeyboardEvent) => { if (event.key === "Escape") close(); };
    const scroll = (event: Event) => { if (!(event.target instanceof Node) || !document.getElementById(id)?.contains(event.target)) close(); };
    window.addEventListener("keydown", escape);
    window.addEventListener("resize", close);
    window.addEventListener("scroll", scroll, true);
    close();
    return () => { close(); window.removeEventListener("keydown", escape); window.removeEventListener("resize", close); window.removeEventListener("scroll", scroll, true); };
  }, [date, viewMode, id]);
  function moveFocus(day: string) {
    dismiss();
    const target = grid.current?.querySelector<HTMLButtonElement>(`[data-calendar-day="${day}"]`);
    if (target) { target.focus(); return; }
    onNavigate(day);
    requestAnimationFrame(() => grid.current?.querySelector<HTMLButtonElement>(`[data-calendar-day="${day}"]`)?.focus());
  }
  const cells = viewMode === "month" ? getMonthDates(date) : getWeekDates(date);
  const week = getWeekDates(date);
  const previewEntries = preview ? entries.get(preview.date) || [] : [];
  return <>
    <div ref={grid} aria-busy={loading} data-testid={`calendar-board-${viewMode}`} className="overflow-hidden rounded-card border border-platforma-border bg-platforma-card shadow-xs">
      <div className={cn("grid grid-cols-7 border-b border-platforma-border bg-surface-muted", viewMode === "week" && "hidden md:grid")}>
        {week.map(day => <div key={day.getDay()} className="py-2 text-center text-xs font-semibold text-platforma-muted">{new Intl.DateTimeFormat(locale, { weekday: "short" }).format(day)}</div>)}
      </div>
      <div className={cn("grid gap-px bg-platforma-border", viewMode === "month" ? "grid-cols-7" : "grid-cols-1 md:grid-cols-7")}>
        {cells.map((cell, index) => {
          if (!cell) return <div key={`empty-${index}`} className="bg-surface-muted/80" />;
          const day = toDateInputValue(cell);
          const rows = entries.get(day) || [];
          const count = rows.filter(row => row.kind === "appointment").length;
          const taskCount = rows.length - count;
          return <button key={day} type="button" data-calendar-day={day} data-focus-return-id={`calendar-day-${day}`}
            aria-label={`${formatPickerDate(day, locale)}. ${loading ? t("common.loadingData") : `${t("calendar.bookings")}: ${count}${canViewTasks ? `. ${t("calendar.tasksToday")}: ${taskCount}` : ""}`}`}
            aria-pressed={day === date} aria-current={day === today ? "date" : undefined} aria-describedby={preview?.date === day ? id : undefined}
            className={cn("platforma-focus-ring group flex min-w-0 flex-col items-stretch justify-start bg-platforma-card p-1.5 text-left transition hover:bg-surface-hover sm:p-2.5", viewMode === "month" ? "min-h-28 sm:min-h-36" : "min-h-28 md:min-h-72", day === date && "bg-brand-50/50 ring-1 ring-inset ring-brand-400")}
            onClick={() => { dismiss(); onSelectDay(day); }}
            onPointerEnter={event => { if (event.pointerType === "mouse") show(day, event.currentTarget); }} onPointerLeave={deferHide}
            onFocus={event => show(day, event.currentTarget)} onBlur={dismiss}
            onKeyDown={event => {
              const delta = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 }[event.key];
              if (delta !== undefined) { event.preventDefault(); moveFocus(shiftDateValue(day, delta)); }
              if (event.key === "Home" || event.key === "End") { event.preventDefault(); const weekday = (cell.getDay() + 6) % 7; moveFocus(shiftDateValue(day, event.key === "Home" ? -weekday : 6 - weekday)); }
            }}>
            <span className="mb-2 flex items-center gap-1.5">
              <span className={cn("inline-flex h-7 min-w-7 items-center justify-center rounded-full text-sm font-semibold tabular-nums", day === today ? "bg-brand-600 text-white" : "text-platforma-text")}>{cell.getDate()}</span>
              {viewMode === "week" && <span className="text-xs text-platforma-muted md:hidden">{new Intl.DateTimeFormat(locale, { weekday: "long", month: "short" }).format(cell)}</span>}
              {!loading && !!rows.length && <span className="ml-auto text-[10px] tabular-nums text-platforma-muted sm:text-xs">{rows.length}</span>}
            </span>
            {!loading && <span aria-hidden="true" className="block space-y-1">
              {rows.slice(0, viewMode === "week" ? 5 : 3).map(row => <span key={row.key} className={cn("block overflow-hidden rounded px-1 py-1 text-[10px] leading-4 sm:text-xs", row.kind === "task" ? "bg-amber-50 text-amber-900" : "bg-brand-50 text-brand-950")}>
                <span className="block truncate"><span className="font-semibold tabular-nums">{formatTime(row.at, locale, timeZone)}</span><span className={cn("ml-1", viewMode === "month" && "hidden sm:inline")}>{row.title}</span></span>
                {viewMode === "week" && row.detail && <span className="block truncate text-platforma-muted">{row.detail}</span>}
              </span>)}
              {rows.length > (viewMode === "week" ? 5 : 3) && <span className="block px-1 text-xs font-semibold text-platforma-muted">+{rows.length - (viewMode === "week" ? 5 : 3)}</span>}
              {!rows.length && viewMode === "week" && <span className="block px-1 text-xs text-platforma-muted">{t("calendar.dayEmpty")}</span>}
            </span>}
          </button>;
        })}
      </div>
    </div>
    {preview && createPortal(<div id={id} role="tooltip" data-testid="calendar-day-preview" onPointerEnter={cancelTimer} onPointerLeave={deferHide}
      style={{ left: preview.left, top: preview.top }} className="fixed z-40 max-h-[min(340px,calc(100dvh-16px))] w-80 max-w-[calc(100vw-16px)] overflow-y-auto rounded-card border border-platforma-border bg-platforma-card p-4 shadow-premium">
      <p className="text-sm font-semibold">{formatPickerDate(preview.date, locale)}</p>
      <div className="mt-3 space-y-2">{previewEntries.slice(0, 6).map(row => <div key={row.key} className="flex gap-3 text-xs">
        <span className="shrink-0 font-semibold tabular-nums text-platforma-muted">{formatTime(row.at, locale, timeZone)}</span>
        <span className="min-w-0"><span className="block break-words font-medium">{row.title}</span><span className="block text-platforma-muted">{row.kind === "task" ? t("calendar.tasksToday") : row.detail}</span></span>
      </div>)}{previewEntries.length > 6 && <p className="text-xs text-platforma-muted">+{previewEntries.length - 6}</p>}
      {!previewEntries.length && <p className="text-xs text-platforma-muted">{t("calendar.dayEmpty")}</p>}</div>
    </div>, document.body)}
  </>;
}

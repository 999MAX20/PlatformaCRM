import { ArrowLeft, ChevronLeft, ChevronRight, Plus, X } from "lucide-react";
import { useEffect, useRef, type ReactNode } from "react";
import { Link } from "react-router";
import { Button } from "../../../components/ui/Button";
import { Drawer } from "../../../components/ui/Overlay";
import { LoadingState } from "../../../components/ui/StateViews";
import type { Appointment, Client, Resource, Service, Task } from "../../../types";
import type { CalendarTranslate } from "../calendarTypes";
import { formatPickerDate, shiftDateValue } from "../calendarUtils";
import { CalendarAppointmentPreview, CalendarTaskPreview } from "./CalendarAppointmentCards";

export function CalendarDayInspector({ open, loading, canViewTasks, date, locale, timeZone, dayAppointments, dayTasks, clientById, serviceById, resourceById, selectedAppointmentId, children, canCreate, hoursLabel, hoursUrl, availableSlots, onClose, onBack, onDayChange, onBooking, onSelectAppointment, onOpenCard, t }: {
  open: boolean; loading: boolean; canViewTasks: boolean; date: string; locale: string; timeZone: string; dayAppointments: Appointment[]; dayTasks: Task[];
  clientById: Map<number, Client>; serviceById: Map<number, Service>; resourceById: Map<number, Resource>;
  selectedAppointmentId: number | null; children?: ReactNode; canCreate: boolean; hoursLabel: string;
  hoursUrl?: string; availableSlots?: number; onClose: () => void; onBack: () => void;
  onDayChange: (date: string) => void; onBooking: (date: string) => void;
  onSelectAppointment: (appointment: Appointment) => void; onOpenCard: (appointment: Appointment) => void; t: CalendarTranslate;
}) {
  const content = useRef<HTMLDivElement>(null);
  const back = useRef<HTMLButtonElement>(null);
  const previous = useRef<number | null>(null);
  useEffect(() => {
    if (selectedAppointmentId) back.current?.focus();
    else if (previous.current) content.current?.querySelector<HTMLButtonElement>(`[data-appointment-id="${previous.current}"]`)?.focus();
    previous.current = selectedAppointmentId;
  }, [selectedAppointmentId]);
  return <Drawer open={open} onClose={onClose} size="detail" ariaLabel={`${t("calendar.selectedDay")}: ${formatPickerDate(date, locale)}`} testId="calendar-day-inspector">
    <header className="shrink-0 border-b border-platforma-border px-4 py-4 sm:px-6">
      <div className="flex items-center justify-between gap-3">
        {selectedAppointmentId ? <Button ref={back} variant="ghost" size="sm" onClick={onBack}><ArrowLeft size={16} />{t("common.back")}</Button> : <span className="text-xs font-semibold text-platforma-muted">{t("calendar.selectedDay")}</span>}
        <Button variant="ghost" size="icon" aria-label={t("common.close")} onClick={onClose}><X size={20} /></Button>
      </div>
      <div className="mt-2 flex items-center gap-2">
        <h2 className="min-w-0 flex-1 text-lg font-semibold">{formatPickerDate(date, locale)}</h2>
        <Button variant="ghost" size="icon" aria-label={t("calendar.previousDay")} onClick={() => onDayChange(shiftDateValue(date, -1))}><ChevronLeft size={18} /></Button>
        <Button variant="ghost" size="icon" aria-label={t("calendar.nextDay")} onClick={() => onDayChange(shiftDateValue(date, 1))}><ChevronRight size={18} /></Button>
      </div>
      <p className="mt-1 text-xs text-platforma-muted">{hoursLabel}</p>
    </header>
    <div ref={content} className="min-h-0 flex-1 overflow-y-auto px-4 py-5 sm:px-6">
      {loading ? <LoadingState /> : selectedAppointmentId ? children : <>
        <div className="mb-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-platforma-muted">
          <span>{t("calendar.bookings")}: <strong className="text-platforma-text">{dayAppointments.length}</strong></span>
          {canViewTasks && <span>{t("calendar.tasksToday")}: <strong className="text-platforma-text">{dayTasks.length}</strong></span>}
          {availableSlots !== undefined && <span>{t("calendar.openSlots")}: <strong className="text-platforma-text">{availableSlots}</strong></span>}
        </div>
        <div className="mb-6 flex flex-wrap items-center gap-3">
          {canCreate && <Button onClick={() => onBooking(date)}><Plus size={16} />{t("calendar.newBooking")}</Button>}
          {hoursUrl && <Link className="platforma-focus-ring text-sm font-medium text-brand-700" to={hoursUrl}>{t("appointment.openHours")}</Link>}
        </div>
        <h3 className="mb-3 text-sm font-semibold">{t("calendar.bookings")}</h3>
        <div className="space-y-2">{dayAppointments.map(appointment => <CalendarAppointmentPreview key={appointment.id} appointment={appointment} selectedAppointmentId={null} clientById={clientById} serviceById={serviceById} resourceById={resourceById} locale={locale} businessTimeZone={timeZone} onSelect={onSelectAppointment} onOpenCard={onOpenCard} t={t} />)}
          {!dayAppointments.length && <p className="rounded-control border border-dashed border-platforma-border p-4 text-sm text-platforma-muted">{t("calendar.dayEmpty")}</p>}
        </div>
        {!!dayTasks.length && <section className="mt-6"><h3 className="mb-3 text-sm font-semibold">{t("calendar.tasksToday")}</h3><div className="divide-y divide-platforma-border overflow-hidden rounded-control border border-platforma-border">{dayTasks.map(task => <CalendarTaskPreview key={task.id} task={task} locale={locale} businessTimeZone={timeZone} t={t} />)}</div></section>}
      </>}
    </div>
  </Drawer>;
}

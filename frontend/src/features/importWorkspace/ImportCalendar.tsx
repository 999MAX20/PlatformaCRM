import { useState } from "react";
import type { ImportReport, ImportReportRow, ImportSource } from "../../api/importWorkspace";
import { CalendarBoard } from "../calendar/components/CalendarBoard";
import { CalendarAppointmentPreview } from "../calendar/components/CalendarAppointmentCards";
import { dateInTimeZone } from "../../lib/format";
import { Input } from "../../components/ui/Input";
import { useI18n } from "../../lib/i18n";
import type { Appointment, Id } from "../../types";
import { describeImportErrors, displayImportValue } from "./importViewModel";

export function ImportCalendar({ report, sources, business, timezone, onSelect, onEdit }: {
  report: ImportReport; sources: ImportSource[]; business: Id; timezone: string; onSelect: (row: ImportReportRow) => void; onEdit: (source: number, row: number) => void;
}) {
  const { t, language } = useI18n();
  const entries = [
    ...(report.rows || []).filter(row => row.entity_type === "appointments" && row.outcome !== "skipped").map(row => ({ row, error: null as unknown })),
    ...(report.errors || []).filter(row => row.entity_type === "appointments").map(row => ({ row, error: row.errors })),
  ].filter(({ row }) => row.values.start_at && row.values.end_at && Number.isFinite(Date.parse(String(row.values.start_at))) && Number.isFinite(Date.parse(String(row.values.end_at))));
  const appointments = entries.map(({ row }, index): Appointment => ({ id: index + 1, business, client: null, client_name: String(row.values.client_name || ""), lead: null,
    service: 0, service_name: String(row.values.service_name || ""), resource: null, resource_name: String(row.values.specialist_name || ""), start_at: String(row.values.start_at), end_at: String(row.values.end_at), status: (row.values.status || "created") as Appointment["status"], source: "manual", notes: String(row.values.notes || ""), created_at: "", updated_at: "" }));
  const today = dateInTimeZone(new Date().toISOString(), timezone);
  const [day, setDay] = useState(appointments[0] ? dateInTimeZone(appointments[0].start_at, timezone) : today);
  const visible = appointments.filter(item => dateInTimeZone(item.start_at, timezone) === day);
  return <div className="space-y-3">
    <Input type="date" label={t("importWorkspace.field.start_at")} value={day} onChange={event => { if (/^\d{4}-\d{2}-\d{2}$/.test(event.target.value)) setDay(event.target.value); }} />
    <CalendarBoard loading={false} canViewTasks={false} date={day} viewMode="week" today={today} locale={language} timeZone={timezone} appointments={appointments} tasks={[]} onSelectDay={setDay} onNavigate={setDay} t={t} />
    <div className="grid gap-3 md:grid-cols-2">{visible.map(appointment => {
      const entry = entries[Number(appointment.id) - 1];
      const select = () => entry.error ? onEdit(entry.row.source_id, entry.row.row) : onSelect(entry.row as ImportReportRow);
      return <div key={entry.row.reference} className={entry.error ? "rounded-control border-2 border-platforma-danger p-2" : ""}>
        <CalendarAppointmentPreview appointment={appointment} customLabels={(sources.find(source => source.id === entry.row.source_id)?.fields || []).filter(field => field.in_calendar).slice(0, 2).flatMap(field => {
          const value = (entry.row as ImportReportRow).custom?.[field.key]?.value;
          return value === undefined || value === null || value === "" ? [] : [{ label: field.label, value: typeof value === "boolean" ? t(value ? "crmCard.yes" : "crmCard.no") : displayImportValue(value) }];
        })} clientById={new Map()} serviceById={new Map()} resourceById={new Map()} selectedAppointmentId={null} locale={language} businessTimeZone={timezone} t={t} onSelect={select} onOpenCard={select} />
        {!!entry.error && <p role="alert" className="mt-2 break-words text-sm text-platforma-danger">{describeImportErrors(entry.error, t)}</p>}
      </div>;
    })}</div>
    {!visible.length && <p className="text-sm text-platforma-muted">{t("importWorkspace.noRows")}</p>}
  </div>;
}

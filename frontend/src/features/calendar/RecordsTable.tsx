import { Link, useLocation } from "react-router";
import { CrmDataTable } from "../../components/crm/CrmDataTable";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { Badge } from "../../components/ui/Badge";
import { formatDateTime } from "../../lib/format";
import { useI18n } from "../../lib/i18n";
import type { Appointment } from "../../types";

export function RecordsTable({ records, timeZone, showBranch = false }: { records: Appointment[]; timeZone: string; showBranch?: boolean }) {
  const { t, language } = useI18n();
  const location = useLocation();
  const returnState = { recordReturnTo: location.pathname + location.search };
  const status = (record: Appointment) => <span className="inline-flex flex-wrap items-center gap-1">
    {["created", "confirmed", "rescheduled"].includes(record.status) ? <Badge variant="info">{t("records.planned")}</Badge> : <StatusBadge status={record.status} />}
    {record.status === "confirmed" ? <span className="text-xs text-platforma-subtle">{t("status.confirmed")}</span> : null}
  </span>;
  const title = (record: Appointment) => record.client_name || `${t("appointments.card")} #${record.id}`;
  return <CrmDataTable>
    <div className="hidden overflow-x-auto md:block">
      <table className="w-full text-left text-sm" aria-label={t("appointments.title")}>
        <thead className="border-b border-platforma-border bg-surface-muted text-platforma-subtle">
          <tr>{["appointments.dateTime", "nav.clients", "records.service", "records.specialist", "records.status", ...(showBranch ? ["records.branch"] : [])].map(key =>
            <th key={key} scope="col" className="px-4 py-3 font-medium">{t(key)}</th>)}</tr>
        </thead>
        <tbody>{records.map(record => <tr key={record.id} className="border-b border-platforma-border last:border-0 hover:bg-surface-hover">
          <td className="whitespace-nowrap px-4 py-3">{formatDateTime(record.start_at, timeZone, true, language)}</td>
          <td className="px-4 py-3"><Link className="platforma-focus-ring rounded font-medium text-brand-700 underline-offset-4 hover:underline" state={returnState} to={`/app/appointments/${record.id}`}>{title(record)}</Link></td>
          <td className="px-4 py-3">{record.service_name}</td><td className="px-4 py-3">{record.resource_name}</td>
          <td className="px-4 py-3">{status(record)}</td>{showBranch && <td className="px-4 py-3">{record.branch_name}</td>}
        </tr>)}</tbody>
      </table>
    </div>
    <ul className="divide-y divide-platforma-border md:hidden">{records.map(record => <li key={record.id} className="space-y-2 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2"><Link className="platforma-focus-ring rounded font-semibold text-brand-700" state={returnState} to={`/app/appointments/${record.id}`}>{title(record)}</Link>{status(record)}</div>
      <p className="text-sm">{formatDateTime(record.start_at, timeZone, true, language)}</p>
      <p className="text-sm text-platforma-subtle">{[record.service_name, record.resource_name, record.branch_name].filter(Boolean).join(" · ")}</p>
    </li>)}</ul>
  </CrmDataTable>;
}

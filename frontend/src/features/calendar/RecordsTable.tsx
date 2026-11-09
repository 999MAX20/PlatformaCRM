import { useCustomColumns } from "../../components/crm/CustomFieldColumns";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { Link, useLocation, useNavigate } from "react-router";
import type { MouseEvent, KeyboardEvent, ReactNode } from "react";
import { CrmDataTable } from "../../components/crm/CrmDataTable";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { Badge } from "../../components/ui/Badge";
import { formatDateTime } from "../../lib/format";
import { useI18n } from "../../lib/i18n";
import type { Appointment } from "../../types";

type RecordsTableProps = { records: Appointment[]; timeZone: string; showBranch?: boolean; onOpen?: (id: number) => void };

export function RecordsTable(props: RecordsTableProps) {
  const { business } = useActiveBusiness();
  const customTable = useCustomColumns(business?.id || 0, "appointment", props.records.map(record => record.id));
  return <RecordsTableView {...props} customColumns={customTable.columns} toolbar={customTable.toolbar} />;
}

export function RecordsTableView({ records, timeZone, showBranch = false, onOpen, customColumns, toolbar }: RecordsTableProps & { customColumns: ReturnType<typeof useCustomColumns>["columns"]; toolbar?: ReactNode }) {
  const { t, language } = useI18n();
  const navigate = useNavigate();
  const location = useLocation();
  const openRecord = (id: number) => onOpen ? onOpen(id) : navigate(`/app/appointments/${id}`, { state: { recordReturnTo: location.pathname + location.search } });
  const activate = (event: MouseEvent<HTMLElement> | KeyboardEvent<HTMLElement>, id: number) => {
    if ((event.target as Element).closest("a,button,input,select,textarea,[role='button']")) return;
    if ("key" in event && event.key !== "Enter") return;
    event.preventDefault();
    openRecord(id);
  };
  const status = (record: Appointment) => <span className="inline-flex flex-wrap items-center gap-1">
    {["created", "confirmed", "rescheduled"].includes(record.status) ? <Badge variant="info">{t("records.planned")}</Badge> : <StatusBadge status={record.status} />}
    {record.status === "confirmed" ? <span className="text-xs text-platforma-subtle">{t("status.confirmed")}</span> : null}
  </span>;
  const title = (record: Appointment) => record.client_name || `${t("appointments.card")} #${record.id}`;
  return <CrmDataTable>
    {toolbar}
    <div className="hidden overflow-x-auto md:block">
      <table className="w-full text-left text-sm" aria-label={t("appointments.title")}>
        <thead className="border-b border-platforma-border bg-surface-muted text-platforma-subtle">
          <tr>{["appointment.client", "appointments.dateTime", "records.service", "records.specialist", "records.status", ...(showBranch ? ["records.branch"] : [])].map(key =>
            <th key={key} scope="col" className="px-4 py-3 font-medium">{t(key)}</th>)}{customColumns.map(column => <th key={column.id} scope="col" className="px-4 py-3 font-medium">{column.header}</th>)}</tr>
        </thead>
        <tbody>{records.map(record => <tr key={record.id} tabIndex={0} aria-label={`${t("appointments.card")} #${record.id}`} onClick={event => activate(event, record.id)} onKeyDown={event => { if (event.target === event.currentTarget) activate(event, record.id); }} className="platforma-focus-ring cursor-pointer border-b border-platforma-border last:border-0 hover:bg-surface-hover focus-visible:bg-surface-hover">
          <td className="px-4 py-3">{record.client ? <Link className="platforma-focus-ring rounded font-medium text-brand-700 underline-offset-4 hover:underline" to={`/app/clients/${record.client}`}>{title(record)}</Link> : title(record)}</td>
          <td className="whitespace-nowrap px-4 py-3">{formatDateTime(record.start_at, timeZone, true, language)}</td>
          <td className="px-4 py-3">{record.service_name}</td><td className="px-4 py-3">{record.resource_name}</td>
          <td className="px-4 py-3">{status(record)}</td>{showBranch && <td className="px-4 py-3">{record.branch_name}</td>}
          {customColumns.map(column => <td key={column.id} className="max-w-64 truncate px-4 py-3">{column.cell(record)}</td>)}
        </tr>)}</tbody>
      </table>
    </div>
    <ul className="divide-y divide-platforma-border md:hidden">{records.map(record => <li key={record.id} onClick={event => activate(event, record.id)} className="cursor-pointer space-y-2 p-4 hover:bg-surface-hover">
      <div className="flex flex-wrap items-center justify-between gap-2">{record.client ? <Link className="platforma-focus-ring rounded font-semibold text-brand-700" to={`/app/clients/${record.client}`}>{title(record)}</Link> : title(record)}{status(record)}</div>
      <button type="button" className="platforma-focus-ring rounded text-left text-sm" aria-label={`${t("appointments.card")} #${record.id}`} onClick={() => openRecord(record.id)}>{formatDateTime(record.start_at, timeZone, true, language)}</button>
      <p className="text-sm text-platforma-subtle">{[record.service_name, record.resource_name, record.branch_name].filter(Boolean).join(" · ")}</p>
      {!!customColumns.length && <dl className="grid grid-cols-2 gap-2 text-sm">{customColumns.map(column => <div key={column.id}><dt className="text-xs text-platforma-muted">{column.header}</dt><dd>{column.cell(record)}</dd></div>)}</dl>}
    </li>)}</ul>
  </CrmDataTable>;
}

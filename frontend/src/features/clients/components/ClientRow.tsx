import { memo, type ReactNode } from "react";
import { formatDateTime } from "../../../lib/format";
import { useI18n } from "../../../lib/i18n";
import { useActiveBusiness } from "../../../hooks/useBusiness";
import type { ClientTableRow, ClientTableColumn, Translate } from "../types";
import { sourceLabel } from "../utils";
import { ClientStatusBadge } from "./ClientPrimitives";

export const ClientRow = memo(function ClientRow({ row, visibleColumns, customCells, onOpen, t }: {
  row: ClientTableRow;
  customCells?: ReactNode;
  visibleColumns: Set<ClientTableColumn>;
  onOpen: () => void;
  t: Translate;
}) {
  const { language } = useI18n();
  const { business } = useActiveBusiness();
  const timezone = business?.timezone || "Asia/Qyzylorda";
  return <tr role="row" tabIndex={0} aria-label={`${t("clients.details")}: ${row.client.full_name}`}
    className="platforma-focus-ring cursor-pointer border-b border-platforma-border last:border-0 hover:bg-surface-hover focus-visible:bg-surface-hover"
    onClick={event => { if (!(event.target as Element).closest("button,a,input")) onOpen(); }}
    onKeyDown={event => { if (event.target === event.currentTarget && (event.key === "Enter" || event.key === " ")) { event.preventDefault(); onOpen(); } }}>
    <td role="gridcell" className="px-4 py-3">
      <button type="button" data-testid="client-row-action-open" data-client-id={row.client.id} onClick={onOpen} className="platforma-focus-ring block max-w-full rounded text-left font-medium text-brand-700 underline-offset-4 hover:underline">{row.client.full_name}</button>
      <p className="mt-0.5 text-xs text-platforma-subtle">{row.client.phone || row.client.email || t("clients.noContacts")}</p>
    </td>
    {visibleColumns.has("source") && <td role="gridcell" className="px-4 py-3">{sourceLabel(row.client.source, t)}</td>}
    <td role="gridcell" className="px-4 py-3"><ClientStatusBadge status={row.status} t={t} /></td>
    <td role="gridcell" className="whitespace-nowrap px-4 py-3">{row.lastContactAt ? formatDateTime(row.lastContactAt, timezone, true, language) : t("clients.noContact")}</td>
    <td role="gridcell" className="px-4 py-3"><p>{row.nextStep.title}</p>{row.nextStep.date && <p className="mt-0.5 text-xs text-platforma-subtle">{new Intl.DateTimeFormat(language, { dateStyle: "medium", timeZone: timezone }).format(new Date(row.nextStep.date))}</p>}</td>
    {visibleColumns.has("manager") && <td role="gridcell" className="px-4 py-3">{row.managerUserId ? row.manager : t("clients.unassigned")}</td>}
    {customCells}
  </tr>;
});

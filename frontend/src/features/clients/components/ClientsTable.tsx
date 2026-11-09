import { ArrowDown, ArrowUp, ChevronsUpDown } from "lucide-react";
import { CrmDataTable, CrmPagination } from "../../../components/crm";
import { Button } from "../../../components/ui/Button";
import type { useCustomColumns } from "../../../components/crm/CustomFieldColumns";
import type { ClientTableColumn, ClientTableRow, Translate } from "../types";
import { ClientRow } from "./ClientRow";
import { MobileClientCards } from "./MobileClientCards";

export function ClientsTable({ rows, ordering, onOrderingChange, onOpenClient, totalClients, page, pageSize, onPageChange, onPageSizeChange, hasFilters, onResetFilters, onCreateClient, visibleColumns, customColumns, t }: {
  rows: ClientTableRow[];
  ordering: string;
  onOrderingChange: (ordering: string) => void;
  onOpenClient: (id: number) => void;
  totalClients: number;
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  hasFilters: boolean;
  onResetFilters: () => void;
  onCreateClient?: () => void;
  visibleColumns: Set<ClientTableColumn>;
  customColumns: ReturnType<typeof useCustomColumns>["columns"];
  t: Translate;
}) {
  const headers = [
    { key: "full_name", label: t("clients.client") },
    ...(visibleColumns.has("source") ? [{ key: "source", label: t("clients.source") }] : []),
    { key: "list_status", label: t("clients.status") },
    { key: "last_activity_at", label: t("clients.lastActivity") },
    { key: "next_step_date", label: t("clients.nextStep") },
    ...(visibleColumns.has("manager") ? [{ key: "manager_name", label: t("clients.manager") }] : []),
  ];
  return <>
    <CrmDataTable>
      <div className="hidden overflow-x-auto md:block">
        <table role="grid" aria-label={t("clients.tableAriaLabel")} className="w-full min-w-[880px] text-left text-sm">
          <thead className="border-b border-platforma-border bg-surface-muted text-platforma-subtle"><tr role="row">
            {headers.map(header => {
              const active = ordering.replace(/^-/, "") === header.key;
              const Icon = active ? ordering.startsWith("-") ? ArrowDown : ArrowUp : ChevronsUpDown;
              return <th key={header.key} role="columnheader" aria-sort={active ? ordering.startsWith("-") ? "descending" : "ascending" : "none"} className="whitespace-nowrap px-4 py-3 font-medium">
                <button type="button" className="platforma-focus-ring inline-flex items-center gap-1 rounded text-left" onClick={() => onOrderingChange(ordering === header.key ? `-${header.key}` : header.key)}>{header.label}<Icon size={13} aria-hidden="true" /></button>
              </th>;
            })}
            {customColumns.map(column => <th key={column.id} role="columnheader" className="px-4 py-3 font-medium">{column.header}</th>)}
          </tr></thead>
          <tbody>{rows.map(row => <ClientRow key={row.client.id} row={row} visibleColumns={visibleColumns} onOpen={() => onOpenClient(row.client.id)} t={t}
            customCells={customColumns.map(column => <td key={column.id} role="gridcell" className="max-w-64 break-words px-4 py-3">{column.cell(row.client)}</td>)} />)}</tbody>
        </table>
      </div>
      <MobileClientCards rows={rows} onOpenClient={onOpenClient} customColumns={customColumns} t={t} />
      {!rows.length && <div className="space-y-3 px-6 py-12 text-center">
        <p className="font-semibold">{t(hasFilters ? "clients.notFoundTitle" : "clients.emptyTitle")}</p>
        <p className="text-sm text-platforma-subtle">{t(hasFilters ? "clients.emptyFiltered" : "clients.emptyText")}</p>
        {hasFilters ? <Button variant="secondary" onClick={onResetFilters}>{t("common.reset")}</Button> : onCreateClient && <Button onClick={onCreateClient}>{t("clients.create")}</Button>}
      </div>}
    </CrmDataTable>
    <CrmPagination compact shown={rows.length} total={totalClients} page={page} pageSize={pageSize} onPageChange={onPageChange} onPageSizeChange={onPageSizeChange} previousLabel={t("pagination.previous")} nextLabel={t("pagination.next")} />
  </>;
}

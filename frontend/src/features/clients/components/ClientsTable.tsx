import { useVirtualizer } from "@tanstack/react-virtual";
import { useRef, useState } from "react";
import { ArrowDown, ArrowUp, ChevronsUpDown, MousePointer2, X } from "lucide-react";

import {
  CrmDataTable,
  CrmPagination,
  CRM_TABLE_CONTENT_CLASS,
  CRM_TABLE_EMBEDDED_CLASS,
  CRM_TABLE_ROW_HEIGHT,
} from "../../../components/crm";
import type { ClientTableColumn, ClientTableRow, Translate } from "../types";
import { ClientRow } from "./ClientRow";

export function ClientsTable({
  rows,
  ordering,
  onOrderingChange,
  selectedClientId,
  onSelectClient,
  onOpenClient,
  totalClients,
  page,
  pageSize,
  onPageChange,
  onPageSizeChange,
  hasFilters,
  visibleColumns,
  t,
}: {
  rows: ClientTableRow[];
  ordering: string;
  onOrderingChange: (ordering: string) => void;
  selectedClientId: number | null;
  onSelectClient: (id: number) => void;
  onOpenClient: (id: number) => void;
  totalClients: number;
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  hasFilters: boolean;
  visibleColumns: Set<ClientTableColumn>;
  t: Translate;
}) {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const [checkedRows, setCheckedRows] = useState<Set<number>>(() => new Set());

  const rowVirtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => CRM_TABLE_ROW_HEIGHT,
    overscan: 8,
  });

  const virtualItems = rowVirtualizer.getVirtualItems();
  const topPadding = virtualItems[0]?.start || 0;
  const bottomPadding = Math.max(
    0,
    rowVirtualizer.getTotalSize() -
      (virtualItems[virtualItems.length - 1]?.end || 0),
  );
  const colSpan = 6 + visibleColumns.size;
  const allPageRowsChecked =
    rows.length > 0 && rows.every((row) => checkedRows.has(row.client.id));
  const firstCheckedRow = rows.find((row) => checkedRows.has(row.client.id));

  function toggleRowCheck(clientId: number) {
    setCheckedRows((current) => {
      const next = new Set(current);
      if (next.has(clientId)) next.delete(clientId);
      else next.add(clientId);
      return next;
    });
  }

  function toggleAllPageRows() {
    setCheckedRows((current) => {
      const next = new Set(current);
      if (allPageRowsChecked) rows.forEach((row) => next.delete(row.client.id));
      else rows.forEach((row) => next.add(row.client.id));
      return next;
    });
  }

  function clearCheckedRows() {
    setCheckedRows(new Set());
  }

  function sortHeader(field: string, label: string) {
    const active = ordering.replace(/^-/, "") === field;
    const Icon = active ? ordering.startsWith("-") ? ArrowDown : ArrowUp : ChevronsUpDown;
    return <button type="button" className="platforma-focus-ring inline-flex items-center gap-1 rounded-control text-left" onClick={() => onOrderingChange(ordering === field ? `-${field}` : field)}>
      {label}<Icon size={13} aria-hidden="true" />
    </button>;
  }

  return (
    <CrmDataTable
      className={`${CRM_TABLE_EMBEDDED_CLASS} flex-none md:flex-1`}
      contentClassName={CRM_TABLE_CONTENT_CLASS}
      toolbar={
        checkedRows.size ? (
          <div className="flex flex-col gap-2 text-sm sm:flex-row sm:items-center sm:justify-between">
            <div className="flex min-w-0 flex-wrap items-center gap-2">
              <span className="rounded-lg bg-brand-50 px-2.5 py-1 text-xs font-bold text-brand-700">
                {t("clients.selectedCount", { count: checkedRows.size })}
              </span>
              <button
                type="button"
                className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-platforma-border bg-surface-card px-3 text-xs font-semibold text-platforma-text transition hover:bg-surface-hover"
                onClick={() =>
                  firstCheckedRow && onOpenClient(firstCheckedRow.client.id)
                }
                disabled={!firstCheckedRow}
              >
                <MousePointer2 size={14} />
                {t("clients.openSelected")}
              </button>
              <button
                type="button"
                className="inline-flex h-8 items-center gap-1.5 rounded-lg px-2.5 text-xs font-semibold text-platforma-muted transition hover:bg-surface-hover hover:text-platforma-text"
                onClick={clearCheckedRows}
              >
                <X size={14} />
                {t("clients.clearSelection")}
              </button>
            </div>
          </div>
        ) : undefined
      }
    >
      <div
        ref={scrollRef}
        className="hidden min-h-0 flex-1 overflow-auto md:block"
        aria-label={t("clients.tableScrollArea")}
      >
        <table
          role="grid"
          aria-label={t("clients.tableAriaLabel")}
          aria-describedby="clients-table-description"
          className="w-full min-w-[1040px] table-fixed border-separate border-spacing-0 text-sm [&_tbody_td]:border-b [&_tbody_td]:border-platforma-border"
        >
          <caption id="clients-table-description" className="sr-only">
            {t("clients.tableDescription")}
          </caption>
          <thead className="sticky top-0 z-10">
            <tr
              role="row"
              className="h-10 border-b border-platforma-border bg-surface-muted text-left text-xs font-semibold text-platforma-muted"
            >
              <th role="columnheader" className="w-10 px-3 py-2">
                <input
                  type="checkbox"
                  checked={allPageRowsChecked}
                  readOnly
                  onClick={toggleAllPageRows}
                  className="h-4 w-4 rounded-sm border-platforma-border text-brand-600 focus:ring-brand-500"
                  aria-label={t("clients.selectAllPage")}
                />
              </th>
              <th role="columnheader" className="w-[24%] px-2 py-2">
                {sortHeader("full_name", t("clients.client"))}
              </th>
              {visibleColumns.has("source") ? (
                <th role="columnheader" className="w-[12%] px-2 py-2">
                  {sortHeader("source", t("clients.source"))}
                </th>
              ) : null}
              <th role="columnheader" className="w-[12%] px-2 py-2">
                {sortHeader("list_status", t("clients.status"))}
              </th>
              <th role="columnheader" className="w-[15%] px-2 py-2">
                {sortHeader("last_activity_at", t("clients.lastContact"))}
              </th>
              <th role="columnheader" className="px-2 py-2">
                {sortHeader("next_step_date", t("clients.nextStep"))}
              </th>
              {visibleColumns.has("manager") ? (
                <th role="columnheader" className="w-[15%] px-2 py-2">
                  {sortHeader("manager_name", t("clients.manager"))}
                </th>
              ) : null}
              <th
                role="columnheader"
                className="w-14 px-2 py-2 text-right"
              ></th>
            </tr>
          </thead>
          <tbody>
            {topPadding ? (
              <tr>
                <td colSpan={colSpan} style={{ height: topPadding }} />
              </tr>
            ) : null}
            {virtualItems.map((virtualRow) => {
              const row = rows[virtualRow.index];
              if (!row) return null;
              return (
                <ClientRow
                  key={row.client.id}
                  row={row}
                  selected={selectedClientId === row.client.id}
                  checked={checkedRows.has(row.client.id)}
                  visibleColumns={visibleColumns}
                  onSelect={() => onSelectClient(row.client.id)}
                  onOpen={() => onOpenClient(row.client.id)}
                  onToggleCheck={() => toggleRowCheck(row.client.id)}
                  t={t}
                />
              );
            })}
            {bottomPadding ? (
              <tr>
                <td colSpan={colSpan} style={{ height: bottomPadding }} />
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      {!rows.length ? (
        <div className="px-6 py-12 text-center">
          <p className="font-bold text-platforma-text">
            {hasFilters ? t("clients.notFoundTitle") : t("clients.emptyTitle")}
          </p>
          <p className="mt-1 text-sm text-platforma-muted">
            {hasFilters ? t("clients.emptyFiltered") : t("clients.emptyText")}
          </p>
        </div>
      ) : null}

      <CrmPagination
        numbered
        pageSizeAriaLabel={t("leads.pageSize")}
        shown={rows.length}
        total={totalClients}
        page={page}
        pageSize={pageSize}
        onPageChange={onPageChange}
        onPageSizeChange={(nextPageSize) => {
          onPageSizeChange(nextPageSize);
        }}
        rangeLabel={t("pagination.range", {
          from: totalClients === 0 ? 0 : (page - 1) * pageSize + 1,
          to: Math.min(totalClients, page * pageSize),
          total: totalClients,
        })}
        previousLabel={t("pagination.previous")}
        nextLabel={t("pagination.next")}
        pageSizeLabel={(size) => t("pagination.pageSize", { size })}
      />
    </CrmDataTable>
  );
}

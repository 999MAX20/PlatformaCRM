import { useCrmFilters } from "../../../components/crm/useCrmFilters";
import type React from "react";
import { CheckCheck, Inbox } from "lucide-react";

import {
  CrmDataTable,
  CrmTableSurface,
  CRM_TABLE_CHECKBOX_COLUMN,
  CRM_TABLE_HEADER_GRID_CLASS,
  CRM_TABLE_MIN_WIDTH,
  CRM_TABLE_WIDE_MIN_WIDTH,
} from "../../../components/crm";
import { Button } from "../../../components/ui/Button";
import { cn } from "../../../lib/cn";
import type { Client, Id, Lead, Service, TeamMember } from "../../../types";
import {
  leadColumnWidths,
  type LeadAiInsight,
  type LeadColumnKey,
  type LeadFilter,
  type Translate,
} from "../types";
import { getClient, getService, getSourceLabel } from "../utils/leadFormat";
import { LeadQueueItem } from "./LeadQueueItem";
import { LeadsPagination } from "./LeadsPagination";
import { VirtualizedLeadTableRows } from "./LeadsTable";
import { LeadsToolbar } from "./LeadsToolbar";

type LeadFilterTab = {
  value: LeadFilter;
  label: string;
  count?: number;
};

export function LeadsWorkspaceTable({
  filters,
  error,
  moreMenuOpen,
  columnOrder,
  visibleColumns,
  rows,
  pageRows,
  selected,
  selectedLeadIds,
  clientList,
  serviceList,
  teamList,
  aiInsights,
  allLeads,
  safePage,
  pageCount,
  pageSize,
  visiblePages,
  pageStart,
  pageEnd,
  totalLeadCount,
  t,
  onToggleMoreMenu,
  onToggleColumn,
  onToggleSortByAi,
  onExportCsv,
  onExportExcel,
  onShareView,
  onOpenImport,
  onOpenForms,
  onSelectLead,
  onOpenLead,
  onToggleBulkLead,
  onToggleAllPageRows,
  onAssignLead,
  onCallLead,
  onWhatsAppLead,
  onOpenContextMenu,
  onArchiveLead,
  onTakeLead,
  onPageChange,
  onPageSizeChange,
}: {
  filters: LeadFilterTab[];
  error?: React.ReactNode;
  moreMenuOpen: boolean;
  columnOrder: LeadColumnKey[];
  visibleColumns: Record<LeadColumnKey, boolean>;
  rows: Lead[];
  pageRows: Lead[];
  selected: Lead | null;
  selectedLeadIds: Id[];
  clientList: Client[];
  serviceList: Service[];
  teamList: TeamMember[];
  aiInsights: Map<Id, LeadAiInsight>;
  allLeads: Lead[];
  safePage: number;
  pageCount: number;
  pageSize: number;
  visiblePages: number[];
  pageStart: number;
  pageEnd: number;
  totalLeadCount: number;
  t: Translate;
  onToggleMoreMenu: () => void;
  onToggleColumn: (column: LeadColumnKey) => void;
  onToggleSortByAi: () => void;
  onExportCsv: () => void;
  onExportExcel: () => void;
  onShareView: () => void;
  onOpenImport: () => void;
  onOpenForms?: () => void;
  onOpenCreate: () => void;
  onSelectLead: (lead: Lead) => void;
  onOpenLead: (lead: Lead) => void;
  onToggleBulkLead: (id: Id) => void;
  onToggleAllPageRows: () => void;
  onAssignLead: (lead: Lead, userId?: Id) => void;
  onCallLead: (lead: Lead) => void;
  onWhatsAppLead: (lead: Lead, template?: string) => void;
  onOpenContextMenu: (event: React.MouseEvent, lead: Lead) => void;
  onArchiveLead: (lead: Lead) => void;
  onTakeLead: (lead: Lead) => void;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
}) {
  const activeTableColumns = columnOrder.filter(
    (column) => visibleColumns[column],
  );
  const tableGridTemplateColumns = `${CRM_TABLE_CHECKBOX_COLUMN} ${activeTableColumns.map((column) => leadColumnWidths[column]).join(" ")} 72px minmax(0,1fr)`;
  const tableGridMinWidth =
    activeTableColumns.length > 5
      ? CRM_TABLE_WIDE_MIN_WIDTH
      : CRM_TABLE_MIN_WIDTH;
  const sourceOptions = [
    "",
    "whatsapp",
    "telegram",
    "instagram",
    "website",
    "landing",
    "manual",
    "parser",
    "other",
  ];
  const allPageRowsSelected =
    pageRows.length > 0 &&
    pageRows.every((lead) => selectedLeadIds.includes(lead.id));
  const { hasFilters, reset } = useCrmFilters("leads");

  return (
    <CrmTableSurface
      frameless
      filters={
        <LeadsToolbar
          filters={filters}
          teamList={teamList}
          sourceOptions={sourceOptions.map((item) => ({
            value: item,
            label: item ? getSourceLabel(item, t) : t("leads.allSources"),
          }))}
          moreMenuOpen={moreMenuOpen}
          columnOrder={columnOrder}
          visibleColumns={visibleColumns}
          labels={{
            search: t("leads.search"),
            columns: t("leads.columns"),
            exportCsv: t("leads.exportCsv"),
            exportExcel: t("leads.exportExcel"),
            import: t("leads.import"),
            shareView: t("leads.shareView"),
            column: (column) => t(`leads.column.${column}`),
          }}
          onToggleMoreMenu={onToggleMoreMenu}
          onToggleColumn={onToggleColumn}
          onToggleSortByAi={onToggleSortByAi}
          onExportCsv={onExportCsv}
          onExportExcel={onExportExcel}
          onShareView={onShareView}
          onOpenImport={onOpenImport}
          onOpenForms={onOpenForms}
        />
      }
    >
      {error || <CrmDataTable
        className="flex min-h-0 flex-1 flex-col rounded-none border-0 bg-transparent shadow-none"
        contentClassName="flex min-h-0 flex-1 flex-col"
      >
        <div className="min-h-0 flex-1 overflow-auto">
        {rows.length > 0 ? <div className="sticky top-0 z-10 hidden bg-surface-card lg:block">
          <div
            className={cn(CRM_TABLE_HEADER_GRID_CLASS, "items-center py-1")}
            data-testid="leads-table-header"
            style={{
              gridTemplateColumns: tableGridTemplateColumns,
              minWidth: tableGridMinWidth,
            }}
          >
            <label className="flex h-8 w-8 items-center justify-center">
              <input
                className="peer sr-only"
                type="checkbox"
                checked={allPageRowsSelected}
                onChange={onToggleAllPageRows}
                aria-label={t("leads.selectAll")}
              />
              <span
                className={cn(
                  "grid h-5 w-5 place-items-center rounded-sm border peer-focus-visible:ring-2 peer-focus-visible:ring-brand-500",
                  allPageRowsSelected
                    ? "border-brand-500 bg-brand-500 text-white"
                    : "border-platforma-control bg-surface-card",
                )}
              >
                {allPageRowsSelected ? <CheckCheck size={13} /> : null}
              </span>
            </label>
            {activeTableColumns.map((column) => (
              <span key={column} className={column === "lead" ? "pl-12" : undefined}>{t(`leads.column.${column}`)}</span>
            ))}
            <span className="text-center">{t("leads.actions")}</span>
          </div>
        </div> : null}
        <div className="min-h-0">
          {!rows.length ? (
            <div className="grid h-full min-h-[320px] place-items-center p-5">
              <div className="max-w-sm text-center">
                <div className="mx-auto grid h-12 w-12 place-items-center rounded-xl bg-brand-50 text-brand-700">
                  <Inbox size={22} />
                </div>
                <h3 className="mt-4 text-lg font-bold text-platforma-text">
                  {hasFilters
                    ? t("leads.emptyFilteredTitle")
                    : t("leads.emptyTitle")}
                </h3>
                <p className="mt-2 text-sm font-semibold leading-6 text-platforma-muted">
                  {hasFilters
                    ? t("leads.emptyFilteredText")
                    : t("leads.emptyText")}
                </p>
                <div className="mt-4 flex flex-col justify-center gap-2 sm:flex-row">
                  {hasFilters ? (
                    <Button
                      variant="secondary"
                      onClick={reset}
                    >
                      {t("tasks.resetFilters")}
                    </Button>
                  ) : null}
                </div>
              </div>
            </div>
          ) : (
            <>
              <VirtualizedLeadTableRows
                rows={pageRows}
                selected={selected}
                selectedLeadIds={selectedLeadIds}
                clientList={clientList}
                serviceList={serviceList}
                teamList={teamList}
                aiInsights={aiInsights}
                allLeads={allLeads}
                visibleColumns={visibleColumns}
                columnOrder={columnOrder}
                selectLead={onSelectLead}
                toggleBulkLead={onToggleBulkLead}
                assignLead={onAssignLead}
                openContextMenu={onOpenContextMenu}
                t={t}
              />
              <div className="divide-y divide-platforma-border lg:hidden">
                {pageRows.map((lead) => (
                  <LeadQueueItem
                    key={lead.id}
                    lead={lead}
                    client={getClient(lead, clientList)}
                    service={getService(lead, serviceList)}
                    selected={lead.id === selected?.id}
                    onClick={() => onSelectLead(lead)}
                    onSwipeLeft={() => onArchiveLead(lead)}
                    onSwipeRight={() => onTakeLead(lead)}
                    onLongPress={(event) => {
                      const touch =
                        "touches" in event
                          ? event.touches[0] || event.changedTouches[0]
                          : event;
                      onOpenContextMenu(
                        {
                          ...event,
                          clientX: touch?.clientX || window.innerWidth / 2,
                          clientY: touch?.clientY || window.innerHeight / 2,
                        } as React.MouseEvent,
                        lead,
                      );
                    }}
                    t={t}
                  />
                ))}
              </div>
            </>
          )}
        </div>
        </div>
        {rows.length > 0 ? <LeadsPagination
          page={safePage}
          pageSize={pageSize}
          total={totalLeadCount}
          shown={pageRows.length}
          label={t("leads.tableShowingRange", {
            start: pageStart,
            end: pageEnd,
            total: totalLeadCount,
          })}
          pageSizeLabel={t("leads.pageSize")}
          previousLabel={t("pagination.previous")}
          nextLabel={t("pagination.next")}
          onPageChange={onPageChange}
          onPageSizeChange={onPageSizeChange}
        /> : null}
      </CrmDataTable>}
    </CrmTableSurface>
  );
}

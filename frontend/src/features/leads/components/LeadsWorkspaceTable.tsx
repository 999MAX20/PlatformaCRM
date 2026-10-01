import type React from "react";
import { CheckCheck, Plus, SlidersHorizontal } from "lucide-react";

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
  type FilterPreset,
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
  count: number;
};

export function LeadsWorkspaceTable({
  filters,
  filter,
  search,
  source,
  savedFiltersOpen,
  filterPresets,
  presetName,
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
  onFilterChange,
  onSearchChange,
  onSourceChange,
  onToggleSavedFilters,
  onApplyPreset,
  onPresetNameChange,
  onSavePreset,
  onToggleMoreMenu,
  onToggleColumn,
  onToggleSortByAi,
  onExportCsv,
  onExportExcel,
  onShareView,
  onOpenImport,
  onOpenCreate,
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
  filter: LeadFilter;
  search: string;
  source: string;
  savedFiltersOpen: boolean;
  filterPresets: FilterPreset[];
  presetName: string;
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
  onFilterChange: (filter: LeadFilter) => void;
  onSearchChange: (value: string) => void;
  onSourceChange: (value: string) => void;
  onToggleSavedFilters: () => void;
  onApplyPreset: (preset: FilterPreset) => void;
  onPresetNameChange: (value: string) => void;
  onSavePreset: () => void;
  onToggleMoreMenu: () => void;
  onToggleColumn: (column: LeadColumnKey) => void;
  onToggleSortByAi: () => void;
  onExportCsv: () => void;
  onExportExcel: () => void;
  onShareView: () => void;
  onOpenImport: () => void;
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
  const tableGridTemplateColumns = `${CRM_TABLE_CHECKBOX_COLUMN} ${activeTableColumns.map((column) => leadColumnWidths[column]).join(" ")} 56px`;
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
    "manual",
    "parser",
    "other",
  ];
  const allPageRowsSelected =
    pageRows.length > 0 &&
    pageRows.every((lead) => selectedLeadIds.includes(lead.id));
  const hasFilters =
    filter !== "all" || Boolean(search.trim()) || Boolean(source);

  return (
    <CrmTableSurface
      className="rounded-card border border-platforma-border bg-surface-card shadow-card"
      filtersClassName="border-b border-platforma-border bg-surface-card px-4 py-3"
      filters={
        <LeadsToolbar
          filters={filters}
          filter={filter}
          search={search}
          source={source}
          sourceOptions={sourceOptions.map((item) => ({
            value: item,
            label: item ? getSourceLabel(item, t) : t("leads.allSources"),
          }))}
          savedFiltersOpen={savedFiltersOpen}
          filterPresets={filterPresets}
          presetName={presetName}
          moreMenuOpen={moreMenuOpen}
          columnOrder={columnOrder}
          visibleColumns={visibleColumns}
          labels={{
            search: t("leads.search"),
            status: t("leads.filtersLabel"),
            source: t("leads.source"),
            filters: t("leads.filters"),
            columns: t("leads.columns"),
            exportCsv: t("leads.exportCsv"),
            exportExcel: t("leads.exportExcel"),
            import: t("leads.import"),
            noSavedFilters: t("leads.noSavedFilters"),
            filterPresetName: t("leads.filterPresetName"),
            saveFilter: t("leads.saveFilter"),
            sortByHeat: t("leads.sortByHeat"),
            shareView: t("leads.shareView"),
            column: (column) => t(`leads.column.${column}`),
          }}
          onFilterChange={onFilterChange}
          onSearchChange={onSearchChange}
          onSourceChange={onSourceChange}
          onToggleSavedFilters={onToggleSavedFilters}
          onApplyPreset={onApplyPreset}
          onPresetNameChange={onPresetNameChange}
          onSavePreset={onSavePreset}
          onToggleMoreMenu={onToggleMoreMenu}
          onToggleColumn={onToggleColumn}
          onToggleSortByAi={onToggleSortByAi}
          onExportCsv={onExportCsv}
          onExportExcel={onExportExcel}
          onShareView={onShareView}
          onOpenImport={onOpenImport}
        />
      }
    >
      <CrmDataTable
        className="flex min-h-0 flex-1 flex-col rounded-none border-0 bg-transparent shadow-none"
        contentClassName="flex min-h-0 flex-1 flex-col"
      >
        <div className="min-h-0 flex-1 overflow-auto">
        <div className="sticky top-0 z-10 hidden bg-surface-card lg:block">
          <div
            className={CRM_TABLE_HEADER_GRID_CLASS}
            style={{
              gridTemplateColumns: tableGridTemplateColumns,
              minWidth: tableGridMinWidth,
            }}
          >
            <label className="flex h-5 w-5 items-center justify-center">
              <input
                className="peer sr-only"
                type="checkbox"
                checked={allPageRowsSelected}
                onChange={onToggleAllPageRows}
                aria-label={t("leads.selectAll")}
              />
              <span
                className={cn(
                  "grid h-5 w-5 place-items-center rounded border peer-focus-visible:ring-2 peer-focus-visible:ring-brand-500",
                  allPageRowsSelected
                    ? "border-brand-500 bg-brand-500 text-platforma-ink"
                    : "border-platforma-border bg-surface-card",
                )}
              >
                {allPageRowsSelected ? <CheckCheck size={13} /> : null}
              </span>
            </label>
            {activeTableColumns.map((column) => (
              <span key={column}>{t(`leads.column.${column}`)}</span>
            ))}
            <span>{t("leads.actions")}</span>
          </div>
        </div>
        <div className="min-h-0">
          {!rows.length ? (
            <div className="grid h-full min-h-[320px] place-items-center p-5">
              <div className="max-w-sm text-center">
                <div className="mx-auto grid h-12 w-12 place-items-center rounded-xl bg-brand-50 text-brand-700">
                  <Plus size={22} />
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
                      onClick={() => {
                        onFilterChange("all");
                        onSearchChange("");
                        onSourceChange("");
                      }}
                    >
                      {t("tasks.resetFilters")}
                    </Button>
                  ) : (
                    <>
                      <Button onClick={onOpenCreate}>
                        <Plus size={16} /> {t("leads.createFirstLead")}
                      </Button>
                      <Button variant="secondary" onClick={onOpenImport}>
                        <SlidersHorizontal size={16} />{" "}
                        {t("leads.setupIntegrations")}
                      </Button>
                    </>
                  )}
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
        <LeadsPagination
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
        />
      </CrmDataTable>
    </CrmTableSurface>
  );
}

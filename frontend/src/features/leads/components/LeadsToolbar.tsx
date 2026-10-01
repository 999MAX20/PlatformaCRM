import { useI18n } from "../../../lib/i18n";
import { ActionMenu } from "../../../components/ui/ActionMenu";
import { CrmWorkspacePopover } from "../../../components/crm/CrmWorkspacePopover";
import { CrmWorkspaceToolbar } from "../../../components/crm/CrmWorkspaceToolbar";
import {
  Columns3,
  Download,
  Filter,
  Flame,
  Share2,
  Upload,
} from "lucide-react";

import { Button } from "../../../components/ui/Button";
import { Select } from "../../../components/ui/Select";
import type { FilterPreset, LeadColumnKey, LeadFilter } from "../types";

type LeadFilterTab = {
  value: LeadFilter;
  label: string;
  count: number;
};

export function LeadsToolbar({
  filters,
  filter,
  search,
  source,
  sourceOptions,
  savedFiltersOpen,
  filterPresets,
  presetName,
  moreMenuOpen,
  columnOrder,
  visibleColumns,
  labels,
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
}: {
  filters: LeadFilterTab[];
  filter: LeadFilter;
  search: string;
  source: string;
  sourceOptions: { value: string; label: string }[];
  savedFiltersOpen: boolean;
  filterPresets: FilterPreset[];
  presetName: string;
  moreMenuOpen: boolean;
  columnOrder: LeadColumnKey[];
  visibleColumns: Record<LeadColumnKey, boolean>;
  labels: {
    search: string;
    status: string;
    source: string;
    filters: string;
    columns: string;
    exportCsv: string;
    exportExcel: string;
    import: string;
    noSavedFilters: string;
    filterPresetName: string;
    saveFilter: string;
    sortByHeat: string;
    shareView: string;
    column: (column: LeadColumnKey) => string;
  };
  onFilterChange: (filter: LeadFilter) => void;
  onSearchChange: (search: string) => void;
  onSourceChange: (source: string) => void;
  onToggleSavedFilters: () => void;
  onApplyPreset: (preset: FilterPreset) => void;
  onPresetNameChange: (name: string) => void;
  onSavePreset: () => void;
  onToggleMoreMenu: () => void;
  onToggleColumn: (column: LeadColumnKey) => void;
  onToggleSortByAi: () => void;
  onExportCsv: () => void;
  onExportExcel: () => void;
  onShareView: () => void;
  onOpenImport: () => void;
}) {
  const { t } = useI18n();
  return (
    <div data-testid="leads-filter-toolbar">
      <CrmWorkspaceToolbar search={search} searchLabel={labels.search} searchTestId="leads-search-input" onSearchChange={onSearchChange}
        value={filter} tabs={filters} onChange={onFilterChange} ariaLabel={labels.status}
        activeFilters={source ? [{ id: "source", label: labels.source, value: sourceOptions.find((item) => item.value === source)?.label || source }] : []}
        onClearFilter={() => onSourceChange("")}
        actions={<>
          <CrmWorkspacePopover label={labels.filters} icon={<Filter size={16} />} open={savedFiltersOpen} onToggle={onToggleSavedFilters} count={Number(Boolean(source))}>
            <div data-testid="lead-saved-filters-panel" className="space-y-3">
              <Select data-testid="leads-status-filter" value={filter} onChange={(event) => onFilterChange(event.target.value as LeadFilter)} aria-label={labels.status} options={filters.map((item) => ({ value: item.value, label: `${item.label} · ${item.count}` }))} />
              <Select data-testid="leads-source-filter" value={source} onChange={(event) => onSourceChange(event.target.value)} aria-label={labels.source} options={sourceOptions} />
              <div className="flex flex-wrap gap-2">
                {filterPresets.length ? filterPresets.map((preset) => <Button key={preset.id} size="sm" variant="secondary" onClick={() => onApplyPreset(preset)}>{preset.name}</Button>) : <span className="text-xs text-platforma-muted">{labels.noSavedFilters}</span>}
              </div>
              <input className="platforma-focus-ring h-9 w-full rounded-control border border-platforma-border px-3 text-sm" aria-label={labels.filterPresetName} placeholder={labels.filterPresetName} value={presetName} onChange={(event) => onPresetNameChange(event.target.value)} />
              <Button size="sm" variant="secondary" onClick={onSavePreset}>{labels.saveFilter}</Button>
            </div>
          </CrmWorkspacePopover>
          <CrmWorkspacePopover label={labels.columns} icon={<Columns3 size={16} />} open={moreMenuOpen} onToggle={onToggleMoreMenu}>
            {columnOrder.map((column) => <label key={column} className="flex items-center gap-3 rounded-control px-2 py-2 text-sm hover:bg-surface-muted">
              <input type="checkbox" checked={visibleColumns[column]} disabled={column === "lead"} onChange={() => onToggleColumn(column)} />{labels.column(column)}
            </label>)}
          </CrmWorkspacePopover>
          <ActionMenu label={t("leads.moreActions")} items={[
            { key: "import", label: labels.import, icon: Upload, onSelect: onOpenImport },
            { key: "csv", label: labels.exportCsv, icon: Download, onSelect: onExportCsv },
            { key: "excel", label: labels.exportExcel, icon: Download, onSelect: onExportExcel },
            { key: "sort", label: labels.sortByHeat, icon: Flame, onSelect: onToggleSortByAi },
            { key: "share", label: labels.shareView, icon: Share2, onSelect: onShareView },
          ]} />
        </>}
      />
    </div>
  );
}

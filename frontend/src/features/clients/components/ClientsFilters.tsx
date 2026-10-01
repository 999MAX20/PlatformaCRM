import { ChevronDown, Columns3, SlidersHorizontal } from "lucide-react";
import { useMemo } from "react";

import { Button } from "../../../components/ui/Button";
import { CrmWorkspaceToolbar } from "../../../components/crm/CrmWorkspaceToolbar";
import { CrmWorkspacePopover } from "../../../components/crm/CrmWorkspacePopover";
import { Select } from "../../../components/ui/Select";
import type { ClientKpi, ClientQuickFilter, ClientTableColumn, Translate } from "../types";

type FilterChip = {
  id: "search" | "source" | "tag" | "segment";
  label: string;
  value: string;
};

export function ClientsFilters({
  quickFilter,
  onQuickFilterChange,
  search,
  onSearchChange,
  source,
  onSourceChange,
  selectedTag,
  onSelectedTagChange,
  selectedSegment,
  onSelectedSegmentChange,
  tagOptions,
  segmentOptions,
  sourceOptions,
  kpi,
  visibleColumns,
  onToggleColumn,
  onOpenSegment,
  onClearSearch,
  onClearAll,
  t,
}: {
  quickFilter: ClientQuickFilter;
  onQuickFilterChange: (value: ClientQuickFilter) => void;
  search: string;
  onSearchChange: (value: string) => void;
  source: string;
  onSourceChange: (value: string) => void;
  selectedTag: string;
  onSelectedTagChange: (value: string) => void;
  selectedSegment: string;
  onSelectedSegmentChange: (value: string) => void;
  tagOptions: Array<{ value: string | number; label: string }>;
  segmentOptions: Array<{ value: string | number; label: string }>;
  sourceOptions: Array<{ value: string | number; label: string }>;
  kpi: ClientKpi;
  visibleColumns: Set<ClientTableColumn>;
  onToggleColumn: (column: ClientTableColumn) => void;
  onOpenSegment: () => void;
  onClearSearch: () => void;
  onClearAll: () => void;
  t: Translate;
}) {
  const quickFilterOptions = useMemo(
    () =>
      [
        { value: "all" as const, label: t("leads.filterAll"), count: kpi.total },
        { value: "new" as const, label: t("clients.filterNew"), count: kpi.new },
        { value: "vip" as const, label: "VIP", count: kpi.vip },
        { value: "no_reply" as const, label: t("leads.filterUnanswered"), count: kpi.noReply },
        { value: "mine" as const, label: t("clients.filterMine"), count: kpi.mine },
      ],
    [kpi, t],
  );
  const columnOptions = useMemo(
    () => [
      { id: "source" as const, label: t("clients.source") },
      { id: "manager" as const, label: t("clients.manager") },
    ],
    [t],
  );

  const activeFilters: FilterChip[] = [
    search ? { id: "search", label: t("clients.searchFilter"), value: search } : null,
    source ? { id: "source", label: t("clients.source"), value: sourceOptions.find((option) => String(option.value) === source)?.label || source } : null,
    selectedTag ? { id: "tag", label: t("clients.tag"), value: tagOptions.find((option) => String(option.value) === selectedTag)?.label || selectedTag } : null,
    selectedSegment
      ? { id: "segment", label: t("clients.segment"), value: segmentOptions.find((option) => String(option.value) === selectedSegment)?.label || selectedSegment }
      : null,
  ].filter(Boolean) as FilterChip[];

  function removeFilter(id: string) {
    if (id === "search") onClearSearch();
    if (id === "source") onSourceChange("");
    if (id === "tag") onSelectedTagChange("");
    if (id === "segment") onSelectedSegmentChange("");
  }

  const advancedContent = (
    <div className="grid gap-2">
      <div className="grid gap-2 md:grid-cols-2">
        <Select value={source} onChange={(event) => onSourceChange(event.target.value)} options={sourceOptions} className="h-9 text-xs" aria-label={t("clients.source")} />
        <Select value={selectedTag} onChange={(event) => onSelectedTagChange(event.target.value)} options={tagOptions} className="h-9 text-xs" aria-label={t("clients.tag")} />
      </div>
      <div className="grid gap-2 md:grid-cols-2">
        <Button type="button" variant="secondary" size="sm" onClick={onOpenSegment} className="justify-between">
          {t("clients.segment")}
          <ChevronDown size={14} />
        </Button>
        <Select
          value={selectedSegment}
          onChange={(event) => onSelectedSegmentChange(event.target.value)}
          options={segmentOptions}
          className="h-9 text-xs"
          aria-label={t("clients.segment")}
        />
      </div>
      <div className="pt-1 text-right">
        <Button type="button" size="sm" variant="secondary" className="h-8" onClick={onClearAll}>
          {search || source || selectedTag || selectedSegment ? t("common.clear") : t("common.reset")}
        </Button>
      </div>
    </div>
  );

  return (
    <CrmWorkspaceToolbar search={search} searchLabel={t("clients.search")} searchTestId="clients-search-input" onSearchChange={onSearchChange}
      value={quickFilter} tabs={quickFilterOptions} onChange={onQuickFilterChange} activeFilters={activeFilters} onClearFilter={removeFilter}
      onClearAll={onClearAll} clearAllLabel={t("common.clearAll")} ariaLabel={t("clients.filtersAriaLabel")}
      actions={<>
        <CrmWorkspacePopover label={t("clients.filters")} icon={<SlidersHorizontal size={16} />} count={activeFilters.filter((item) => item.id !== "search").length}>{advancedContent}</CrmWorkspacePopover>
        <CrmWorkspacePopover label={t("clients.columns")} icon={<Columns3 size={16} />}>
          {columnOptions.map((column) => <label key={column.id} className="flex items-center gap-3 rounded-control px-2 py-2 text-sm hover:bg-surface-muted">
            <input type="checkbox" checked={visibleColumns.has(column.id)} onChange={() => onToggleColumn(column.id)} />{column.label}
          </label>)}
        </CrmWorkspacePopover>
      </>}
    />
  );
}

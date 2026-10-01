import { SlidersHorizontal, Columns3, List } from "lucide-react";

import { type CrmActiveFilter } from "../../../components/crm";
import { CrmWorkspaceToolbar } from "../../../components/crm/CrmWorkspaceToolbar";
import { CrmWorkspacePopover } from "../../../components/crm/CrmWorkspacePopover";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import type { Pipeline, PipelineStage, TeamMember } from "../../../types";
import type { DealFiltersState, DealQuickFilter, DealStatusFilter, Translate } from "../types";
import { dealPipelineLabel, dealStageLabel, sourceLabel } from "../utils/dealHelpers";

type DealsFiltersProps = {
  filters: DealFiltersState;
  pipelines: Pipeline[];
  activePipeline: number;
  viewMode: "table" | "kanban";
  onViewModeChange: (value: "table" | "kanban") => void;
  stages: PipelineStage[];
  teamMembers: TeamMember[];
  quickCounts: Record<DealQuickFilter, number>;
  onChange: (patch: Partial<DealFiltersState>) => void;
  onReset: () => void;
  t: Translate;
};

const quickFilters: DealQuickFilter[] = ["all", "mine", "hot", "overdue", "no_tasks"];
const statusFilters: DealStatusFilter[] = ["open", "won", "lost", "all"];
const sourceOptions = ["", "manual", "website", "landing", "telegram", "whatsapp", "instagram", "parser", "other"];

function statusLabel(value: DealStatusFilter, t: Translate) {
  const labels: Record<DealStatusFilter, string> = {
    open: t("deals.statusOpen"),
    won: t("deals.statusWon"),
    lost: t("deals.statusLost"),
    all: t("deals.allStatuses"),
  };
  return labels[value];
}

function quickLabel(value: DealQuickFilter, t: Translate) {
  const labels: Record<DealQuickFilter, string> = {
    all: t("common.all"),
    mine: t("deals.filterMine"),
    hot: t("deals.hot"),
    overdue: t("deals.overdue"),
    no_tasks: t("deals.noTasksFilter"),
  };
  return labels[value];
}

export function DealsFilters({ filters, pipelines, activePipeline, viewMode, onViewModeChange, stages, teamMembers, quickCounts, onChange, onReset, t }: DealsFiltersProps) {
  const activeFilters: CrmActiveFilter[] = [
    filters.search ? { id: "search", label: t("common.search"), value: filters.search } : null,
    filters.statusFilter !== "open" ? { id: "statusFilter", label: t("deals.status"), value: statusLabel(filters.statusFilter, t) } : null,
    filters.stageFilter !== "all" ? { id: "stageFilter", label: t("deals.stage"), value: dealStageLabel(stages.find((stage) => String(stage.id) === filters.stageFilter), t) || filters.stageFilter } : null,
    filters.ownerFilter ? { id: "ownerFilter", label: t("deals.manager"), value: teamMembers.find((member) => String(member.user.id) === filters.ownerFilter)?.user.full_name || filters.ownerFilter } : null,
    filters.sourceFilter ? { id: "sourceFilter", label: t("deals.source"), value: sourceLabel(filters.sourceFilter, t) } : null,
    filters.minAmount ? { id: "minAmount", label: t("deals.amountFrom"), value: filters.minAmount } : null,
    filters.maxAmount ? { id: "maxAmount", label: t("deals.amountTo"), value: filters.maxAmount } : null,
    filters.dateFrom ? { id: "dateFrom", label: t("deals.periodFrom"), value: filters.dateFrom } : null,
    filters.dateTo ? { id: "dateTo", label: t("deals.periodTo"), value: filters.dateTo } : null,
  ].filter(Boolean) as CrmActiveFilter[];

  function clearFilter(id: string) {
    if (id === "search") onChange({ search: "" });
    if (id === "statusFilter") onChange({ statusFilter: "open" });
    if (id === "stageFilter") onChange({ stageFilter: "all" });
    if (id === "ownerFilter") onChange({ ownerFilter: "" });
    if (id === "sourceFilter") onChange({ sourceFilter: "" });
    if (id === "minAmount") onChange({ minAmount: "" });
    if (id === "maxAmount") onChange({ maxAmount: "" });
    if (id === "dateFrom") onChange({ dateFrom: "" });
    if (id === "dateTo") onChange({ dateTo: "" });
  }

  return (
    <div data-testid="deals-filter-bar">
      <CrmWorkspaceToolbar search={filters.search} searchLabel={t("deals.queueSearch")} searchTestId="deals-search-input" onSearchChange={(search) => onChange({ search })}
        value={filters.quickFilter} tabs={quickFilters.map((value) => ({ value, label: quickLabel(value, t), count: quickCounts[value] }))}
        onChange={(quickFilter) => onChange({ quickFilter })} activeFilters={activeFilters} onClearFilter={clearFilter} onClearAll={onReset} clearAllLabel={t("deals.reset")} ariaLabel={t("deals.filters")}
        secondaryActions={<Select value={String(activePipeline)} onChange={(event) => onChange({ pipelineId: event.target.value, stageFilter: "all" })} options={pipelines.map((pipeline) => ({ value: String(pipeline.id), label: dealPipelineLabel(pipeline, t) }))} aria-label={t("deals.pipeline")} className="h-9 max-w-56" />}
        actions={<>
          <CrmWorkspacePopover label={t("deals.filters")} icon={<SlidersHorizontal size={16} />} count={activeFilters.filter((item) => item.id !== "search").length}>
        <div className="grid gap-2">
          <div className="grid gap-2 md:grid-cols-2">
            <Select data-testid="deals-status-filter" value={filters.statusFilter} onChange={(event) => onChange({ statusFilter: event.target.value as DealStatusFilter })} options={statusFilters.map((value) => ({ value, label: statusLabel(value, t) }))} className="h-9 text-xs" aria-label={t("deals.status")} />
            <Select value={filters.stageFilter} onChange={(event) => onChange({ stageFilter: event.target.value })} options={[{ value: "all", label: t("deals.allStages") }, ...stages.map((stage) => ({ value: String(stage.id), label: dealStageLabel(stage, t) }))]} className="h-9 text-xs" aria-label={t("deals.stage")} />
            <Select
              value={filters.ownerFilter}
              onChange={(event) => onChange({ ownerFilter: event.target.value })}
              options={[{ value: "", label: t("deals.allManagers") }, ...teamMembers.filter((member) => member.is_active).map((member) => ({ value: String(member.user.id), label: member.user.full_name || member.user.email }))]}
              className="h-9 text-xs"
              aria-label={t("deals.manager")}
            />
            <Select value={filters.sourceFilter} onChange={(event) => onChange({ sourceFilter: event.target.value })} options={sourceOptions.map((value) => ({ value, label: value ? sourceLabel(value, t) : t("clients.allSources") }))} className="h-9 text-xs" aria-label={t("deals.source")} />
          </div>
          <div className="grid gap-2 md:grid-cols-2">
            <Input type="number" value={filters.minAmount} onChange={(event) => onChange({ minAmount: event.target.value })} placeholder={t("deals.amountFrom")} className="h-9 text-xs" aria-label={t("deals.amountFrom")} />
            <Input type="number" value={filters.maxAmount} onChange={(event) => onChange({ maxAmount: event.target.value })} placeholder={t("deals.amountTo")} className="h-9 text-xs" aria-label={t("deals.amountTo")} />
            <Input type="date" value={filters.dateFrom} onChange={(event) => onChange({ dateFrom: event.target.value })} className="h-9 text-xs" aria-label={t("deals.periodFrom")} />
            <Input type="date" value={filters.dateTo} onChange={(event) => onChange({ dateTo: event.target.value })} className="h-9 text-xs" aria-label={t("deals.periodTo")} />
          </div>
          <div className="flex justify-end">
            <Button type="button" size="sm" variant="secondary" className="h-8" onClick={onReset}>
              {t("deals.reset")}
            </Button>
          </div>
        </div>
          </CrmWorkspacePopover>
          <div role="group" aria-label={t("deals.viewTable")} className="flex overflow-hidden rounded-control border border-platforma-border">
            <Button variant="ghost" className="h-10 rounded-none aria-pressed:bg-brand-50 aria-pressed:text-platforma-text" aria-pressed={viewMode === "kanban"} onClick={() => onViewModeChange("kanban")}><Columns3 size={16} />{t("deals.viewKanban")}</Button>
            <Button variant="ghost" className="h-10 rounded-none aria-pressed:bg-brand-50 aria-pressed:text-platforma-text" aria-pressed={viewMode === "table"} onClick={() => onViewModeChange("table")}><List size={16} />{t("deals.viewTable")}</Button>
          </div>
        </>}
      />
    </div>
  );
}

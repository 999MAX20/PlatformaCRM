import { Columns3, List } from "lucide-react";
import { CrmFilterControls } from "../../../components/crm/CrmFilterControls";
import { Button } from "../../../components/ui/Button";
import { Select } from "../../../components/ui/Select";
import type { Pipeline, PipelineStage, TeamMember } from "../../../types";
import type { DealFiltersState, DealQuickFilter, Translate } from "../types";
import { dealPipelineLabel, dealStageLabel, sourceLabel } from "../utils/dealHelpers";
type DealsFiltersProps = {
  filters: DealFiltersState;
  pipelines: Pipeline[];
  activePipeline: number;
  viewMode: "table" | "kanban";
  onViewModeChange: (value: "table" | "kanban") => void;
  stages: PipelineStage[];
  teamMembers: TeamMember[];
  quickCounts: Record<DealQuickFilter, number | undefined>;
  onChange: (patch: Partial<DealFiltersState>) => void;
  onReset: () => void;
  t: Translate;
};

const sources = ["manual", "website", "landing", "telegram", "whatsapp", "instagram", "parser", "other"];
export function DealsFilters({ pipelines, activePipeline, viewMode, onViewModeChange, stages, teamMembers, quickCounts, onChange, t }: DealsFiltersProps) {
  return <div data-testid="deals-filter-bar"><CrmFilterControls kind="deals" searchLabel={t("deals.queueSearch")} counts={{ ...quickCounts, total: quickCounts.all }}
    options={{ source: sources.map(value => ({ value, label: sourceLabel(value, t) })), stage: stages.map(stage => ({ value: stage.id, label: dealStageLabel(stage, t) })), assignees: teamMembers.filter(member => member.is_active).map(member => ({ value: member.user.id, label: member.user.full_name || member.user.email })) }}
    context={pipelines.length > 1 ? <Select value={String(activePipeline)} onChange={event => onChange({ pipelineId: event.target.value, stageFilter: "all" })} options={pipelines.map(pipeline => ({ value: String(pipeline.id), label: dealPipelineLabel(pipeline, t) }))} aria-label={t("deals.pipeline")} className="h-10 max-w-40" /> : null}
    actions={<div role="group" aria-label={t("deals.viewTable")} className="flex overflow-hidden rounded-control border border-platforma-border">
      <Button variant="ghost" size="icon" className="h-10 rounded-none aria-pressed:bg-brand-50" aria-label={t("deals.viewKanban")} title={t("deals.viewKanban")} aria-pressed={viewMode === "kanban"} onClick={() => onViewModeChange("kanban")}><Columns3 size={16} /></Button>
      <Button variant="ghost" size="icon" className="h-10 rounded-none aria-pressed:bg-brand-50" aria-label={t("deals.viewTable")} title={t("deals.viewTable")} aria-pressed={viewMode === "table"} onClick={() => onViewModeChange("table")}><List size={16} /></Button>
    </div>} /></div>;
}

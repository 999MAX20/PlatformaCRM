import {
  canCancelRun,
  canRetryRun,
  runStatusVariant,
  runStatusLabel,
  runStatuses,
} from "./automationPresentation";

import { useAutomationRuns } from "./useAutomationRuns";

import { Ban, Eye, RotateCcw } from "lucide-react";

import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Select } from "../../components/ui/Select";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { CrmPagination } from "../../components/crm/CrmPagination";

import { useI18n } from "../../lib/i18n";

type Props = {
  t: ReturnType<typeof useI18n>["t"];
  runs: ReturnType<typeof useAutomationRuns>["runs"];
  filters: ReturnType<typeof useAutomationRuns>["filters"];
  updateFilters: ReturnType<typeof useAutomationRuns>["updateFilters"];
  canManage: boolean;
  triggers: { value: string; label: string }[];
  locale: string;
  setSelectedRun: ReturnType<typeof useAutomationRuns>["setSelectedRun"];
  retryRunMutation: ReturnType<typeof useAutomationRuns>["retryRunMutation"];
  cancelRunMutation: ReturnType<typeof useAutomationRuns>["cancelRunMutation"];
};
export function AutomationRunList({
  t,
  runs,
  filters,
  updateFilters,
  canManage,
  triggers,
  locale,
  setSelectedRun,
  retryRunMutation,
  cancelRunMutation,
}: Props) {
  const runList = runs.data?.results || [];
  const total = runs.data?.count ?? 0;
  const hasFilters = Boolean(filters.status || filters.triggerType);
  return (
    <section aria-label={t("automations.runsTitle")} className="mt-6" aria-busy={runs.isFetching}>
      <h2 className="text-xl font-bold text-platforma-text">
        {t("automations.runsTitle")}
      </h2>
      <div className="mt-3 grid gap-3 sm:grid-cols-[1fr_1fr_auto]">
        <Select label={t("automations.status")} value={filters.status}
          options={[{ value: "", label: t("common.all") }, ...runStatuses.map(value => ({ value, label: runStatusLabel(value, t) }))]}
          onChange={event => updateFilters({ status: event.target.value })} />
        <Select label={t("automations.trigger")} value={filters.triggerType}
          options={[{ value: "", label: t("common.all") }, ...triggers]}
          onChange={event => updateFilters({ triggerType: event.target.value })} />
        {hasFilters || filters.page > 1 ? <Button variant="ghost" className="self-end"
          onClick={() => updateFilters({ status: "", triggerType: "", page: 1 })}>{t("automations.resetHistory")}</Button> : null}
      </div>
      {retryRunMutation.error || cancelRunMutation.error ? <ErrorState error={retryRunMutation.error || cancelRunMutation.error} /> : null}
      <div className="mt-3 overflow-hidden rounded-card border border-platforma-border bg-surface-card shadow-card">
        {runs.isLoading ? <LoadingState /> : runs.isError ? <ErrorState error={runs.error}
          action={<Button variant="secondary" onClick={() => void runs.refetch()}>{t("common.retry")}</Button>} /> : <>
        {runList.map((run) => (
          <div
            key={run.id}
            data-testid="automation-run-row"
            className="grid gap-2 border-b border-platforma-border px-4 py-3 text-sm last:border-b-0 md:grid-cols-[1fr_120px_160px_auto]"
          >
            <div>
              <p className="font-bold text-platforma-text">
                {triggers.find((item) => item.value === run.trigger_type)
                  ?.label || run.trigger_type}
              </p>
              <p className="text-xs font-semibold leading-5 text-platforma-subtle">
                {run.entity_type || t("automations.entity")} #
                {run.entity_id || "-"} ·{" "}
                {t("automations.attempt", {
                  current: run.attempts || 0,
                  max: run.max_attempts || 3,
                })}
                {run.next_retry_at
                  ? ` · ${t("automations.retryAt", { date: new Date(run.next_retry_at).toLocaleString(locale) })}`
                  : ""}
                {run.error ? ` · ${t("automations.runFailureSummary")}` : ""}
              </p>
            </div>
            <Badge variant={runStatusVariant(run.status)}>
              {runStatusLabel(run.status, t)}
            </Badge>
            <span className="text-xs font-semibold text-platforma-faint">
              {new Date(run.created_at).toLocaleString(locale)}
            </span>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="ghost"
                className="min-h-8 px-3 py-1 text-xs"
                onClick={() => setSelectedRun(run)}
              >
                <Eye size={14} />
                {t("automations.details")}
              </Button>
              {canManage && canRetryRun(run) ? (
                <Button
                  variant="secondary"
                  className="min-h-8 px-3 py-1 text-xs"
                  onClick={() => retryRunMutation.mutate(run.id)}
                  isLoading={retryRunMutation.isPending}
                >
                  <RotateCcw size={14} />
                  {t("automations.retry")}
                </Button>
              ) : null}
              {canManage && canCancelRun(run) ? (
                <Button
                  variant="warning"
                  className="min-h-8 px-3 py-1 text-xs"
                  onClick={() => cancelRunMutation.mutate(run.id)}
                  isLoading={cancelRunMutation.isPending}
                >
                  <Ban size={14} />
                  {t("automations.cancelRun")}
                </Button>
              ) : null}
            </div>
          </div>
        ))}
        {!runList.length ? (
          <div className="px-4 py-5 text-sm font-semibold text-platforma-subtle">
            {t(hasFilters ? "common.noResults" : "automations.noRuns")}
          </div>
        ) : null}
        <CrmPagination shown={runList.length} total={total} page={filters.page} pageSize={filters.pageSize}
          onPageChange={page => updateFilters({ page })} onPageSizeChange={pageSize => updateFilters({ pageSize })}
          previousLabel={t("pagination.previous")} nextLabel={t("pagination.next")}
          pageSizeAriaLabel={t("pagination.pageSizeAriaLabel")} pageSizeLabel={size => t("pagination.pageSize", { size })}
          rangeLabel={t("pagination.range", { from: total ? (filters.page - 1) * filters.pageSize + 1 : 0,
            to: Math.min(total, filters.page * filters.pageSize), total })} />
        </>}
      </div>
    </section>
  );
}

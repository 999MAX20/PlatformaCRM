import {
  canCancelRun,
  canRetryRun,
  runStatusVariant,
  runStatusLabel,
} from "./automationPresentation";

import { useAutomationRuns } from "./useAutomationRuns";

import { Ban, Eye, RotateCcw } from "lucide-react";

import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";

import { useI18n } from "../../lib/i18n";

type Props = {
  t: ReturnType<typeof useI18n>["t"];
  runList: AutomationRun[];
  triggers: { value: string; label: string }[];
  locale: string;
  setSelectedRun: ReturnType<typeof useAutomationRuns>["setSelectedRun"];
  retryRunMutation: ReturnType<typeof useAutomationRuns>["retryRunMutation"];
  cancelRunMutation: ReturnType<typeof useAutomationRuns>["cancelRunMutation"];
};
export function AutomationRunList({
  t,
  runList,
  triggers,
  locale,
  setSelectedRun,
  retryRunMutation,
  cancelRunMutation,
}: Props) {
  return (
    <div className="mt-6">
      <h2 className="text-xl font-bold text-platforma-text">
        {t("automations.runsTitle")}
      </h2>
      <div className="mt-3 overflow-hidden rounded-card border border-platforma-border bg-surface-card shadow-card">
        {runList.slice(0, 8).map((run) => (
          <div
            key={run.id}
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
              {canRetryRun(run) ? (
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
              {canCancelRun(run) ? (
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
            {t("automations.noRuns")}
          </div>
        ) : null}
      </div>
    </div>
  );
}
import type { AutomationRun } from "../../types";

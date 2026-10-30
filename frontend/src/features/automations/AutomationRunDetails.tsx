import {
  formatJson,
  canCancelRun,
  canRetryRun,
  runStatusVariant,
  runStatusLabel,
} from "./automationPresentation";

import { useAutomationRuns } from "./useAutomationRuns";

import { Ban, RotateCcw } from "lucide-react";

import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";

import { Modal } from "../../components/ui/Modal";

import { ErrorState } from "../../components/ui/StateViews";

import { useI18n } from "../../lib/i18n";

type Props = {
  t: ReturnType<typeof useI18n>["t"];
  selectedRun: ReturnType<typeof useAutomationRuns>["selectedRun"];
  setSelectedRun: ReturnType<typeof useAutomationRuns>["setSelectedRun"];
  locale: string;
  retryRunMutation: ReturnType<typeof useAutomationRuns>["retryRunMutation"];
  cancelRunMutation: ReturnType<typeof useAutomationRuns>["cancelRunMutation"];
};
export function AutomationRunDetails({
  t,
  selectedRun,
  setSelectedRun,
  locale,
  retryRunMutation,
  cancelRunMutation,
}: Props) {
  return (
    <Modal
      title={t("automations.runDetailTitle")}
      open={Boolean(selectedRun)}
      onClose={() => setSelectedRun(null)}
    >
      {selectedRun ? (
        <div className="space-y-4 text-sm">
          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <p className="text-xs font-bold uppercase text-platforma-faint">
                {t("automations.status")}
              </p>
              <div className="mt-1">
                <Badge variant={runStatusVariant(selectedRun.status)}>
                  {runStatusLabel(selectedRun.status, t)}
                </Badge>
              </div>
            </div>
            <div>
              <p className="text-xs font-bold uppercase text-platforma-faint">
                {t("automations.runRule")}
              </p>
              <p className="mt-1 font-semibold text-platforma-text">
                {selectedRun.rule_name || selectedRun.rule || "-"}
              </p>
            </div>
            <div>
              <p className="text-xs font-bold uppercase text-platforma-faint">
                {t("automations.runEntity")}
              </p>
              <p className="mt-1 font-semibold text-platforma-text">
                {selectedRun.entity_type || "-"} #{selectedRun.entity_id || "-"}
              </p>
            </div>
            <div>
              <p className="text-xs font-bold uppercase text-platforma-faint">
                {t("automations.attempts")}
              </p>
              <p className="mt-1 font-semibold text-platforma-text">
                {t("automations.attempt", {
                  current: selectedRun.attempts || 0,
                  max: selectedRun.max_attempts || 3,
                })}
              </p>
            </div>
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            <div>
              <p className="text-xs font-bold uppercase text-platforma-faint">
                {t("automations.runCreated")}
              </p>
              <p className="mt-1 text-platforma-subtle">
                {new Date(selectedRun.created_at).toLocaleString(locale)}
              </p>
            </div>
            <div>
              <p className="text-xs font-bold uppercase text-platforma-faint">
                {t("automations.runStarted")}
              </p>
              <p className="mt-1 text-platforma-subtle">
                {selectedRun.started_at
                  ? new Date(selectedRun.started_at).toLocaleString(locale)
                  : "-"}
              </p>
            </div>
            <div>
              <p className="text-xs font-bold uppercase text-platforma-faint">
                {t("automations.runFinished")}
              </p>
              <p className="mt-1 text-platforma-subtle">
                {selectedRun.finished_at
                  ? new Date(selectedRun.finished_at).toLocaleString(locale)
                  : "-"}
              </p>
            </div>
          </div>
          {selectedRun.error ? (
            <ErrorState message={t("automations.runFailureDetails")} />
          ) : null}
          <div>
            <p className="mb-2 text-xs font-bold uppercase text-platforma-muted">
              {t("automations.runPayload")}
            </p>
            <pre className="max-h-48 overflow-auto rounded-card bg-platforma-ink p-3 text-xs text-surface-card">
              {formatJson(selectedRun.payload)}
            </pre>
          </div>
          <div>
            <p className="mb-2 text-xs font-bold uppercase text-platforma-muted">
              {t("automations.runResults")}
            </p>
            <pre className="max-h-48 overflow-auto rounded-card bg-platforma-ink p-3 text-xs text-surface-card">
              {formatJson(selectedRun.action_results || [])}
            </pre>
          </div>
          <div className="flex flex-wrap gap-2">
            {canRetryRun(selectedRun) ? (
              <Button
                type="button"
                variant="secondary"
                onClick={() => retryRunMutation.mutate(selectedRun.id)}
                isLoading={retryRunMutation.isPending}
              >
                <RotateCcw size={16} />
                {t("automations.retry")}
              </Button>
            ) : null}
            {canCancelRun(selectedRun) ? (
              <Button
                type="button"
                variant="warning"
                onClick={() => cancelRunMutation.mutate(selectedRun.id)}
                isLoading={cancelRunMutation.isPending}
              >
                <Ban size={16} />
                {t("automations.cancelRun")}
              </Button>
            ) : null}
          </div>
        </div>
      ) : null}
    </Modal>
  );
}

import { usePricingSafety } from "./usePricingSafety";

import { AlertTriangle } from "lucide-react";

import { Button } from "../../components/ui/Button";

import { useI18n } from "../../lib/i18n";

type Props = {
  control: ReturnType<typeof usePricingSafety>["control"];
  t: ReturnType<typeof useI18n>["t"];
  alerts: ReturnType<typeof usePricingSafety>["alerts"];
  canManage: boolean;
  resumePricing: ReturnType<typeof usePricingSafety>["resumePricing"];
  emergencyStop: ReturnType<typeof usePricingSafety>["emergencyStop"];
};
export function PricingSafetyPanel({
  control,
  t,
  alerts,
  canManage,
  resumePricing,
  emergencyStop,
}: Props) {
  return (
    <section
      className={
        control?.emergency_stop_enabled
          ? "rounded-[2rem] border border-platforma-danger/20 bg-[var(--platforma-danger-soft)] p-5 shadow-soft"
          : "rounded-[2rem] border border-platforma-border bg-white p-5 shadow-soft"
      }
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-start gap-3">
          <AlertTriangle
            className={
              control?.emergency_stop_enabled
                ? "mt-1 text-platforma-danger"
                : "mt-1 text-platforma-warning"
            }
            size={22}
          />
          <div>
            <h2 className="text-lg font-black text-midnight">
              {t("pricing.safetyTitle")}
            </h2>
            <p className="mt-1 text-sm font-semibold text-platforma-subtle">
              {control?.emergency_stop_enabled
                ? t("pricing.agentStopped", {
                    reason:
                      control.emergency_stop_reason || t("pricing.noReason"),
                  })
                : t("pricing.agentActive")}
            </p>
            {alerts.length ? (
              <p className="mt-1 text-sm font-bold text-platforma-warning">
                {t("pricing.openSignals", { count: alerts.length })}
              </p>
            ) : null}
          </div>
        </div>
        {control?.emergency_stop_enabled ? (
          <Button
            disabled={!canManage}
            isLoading={resumePricing.isPending}
            onClick={() => resumePricing.mutate()}
          >
            {t("pricing.resume")}
          </Button>
        ) : (
          <Button
            variant="danger"
            disabled={!canManage}
            isLoading={emergencyStop.isPending}
            onClick={() => emergencyStop.mutate()}
          >
            {t("pricing.stopAgent")}
          </Button>
        )}
      </div>
    </section>
  );
}

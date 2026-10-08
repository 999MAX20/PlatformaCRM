import { Card, CardBody } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { getApiErrorMessage } from "../../../api/client";
import type { EntitlementSummaryItem, UsageSummaryItem } from "../../../types";
import type { Translate } from "../settingsUtils";

type UsageSectionProps = {
  className: string;
  formatMetric: (metric: string, t: Translate) => string;
  isLoading: boolean;
  error: unknown;
  onRetry: () => void;
  locale: string;
  items: Array<EntitlementSummaryItem | UsageSummaryItem>;
  t: Translate;
};

export function UsageSection({
  className,
  formatMetric,
  isLoading,
  error,
  onRetry,
  locale,
  items,
  t,
}: UsageSectionProps) {
  return (
    <Card id="usage" className={className}>
      <CardBody>
        <div className="mb-4">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-brand-700">
            {t("settings.usageEyebrow")}
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-platforma-text">
            {t("settings.usageTitle")}
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-platforma-subtle">
            {t("settings.usageText")}
          </p>
        </div>
        {isLoading ? <LoadingState /> : error ? <ErrorState error={error} message={getApiErrorMessage(error)} action={<Button type="button" variant="secondary" onClick={onRetry}>{t("common.retry")}</Button>} /> : <div className="grid gap-3 md:grid-cols-4">
          {items.map((item) => {
            const percent = item.limit && item.limit > 0
              ? Math.min(100, Math.round((item.value / item.limit) * 100))
              : item.value > 0 ? 100 : 0;
            return (
              <div
                key={item.metric}
                className="rounded-card bg-surface-muted p-4"
              >
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-platforma-faint">
                  {formatMetric(item.metric, t)}
                </p>
                <p className="mt-2 text-2xl font-bold text-platforma-text">
                  {item.value.toLocaleString(locale, { maximumFractionDigits: 2 })}
                  <span className="text-sm font-semibold text-platforma-faint">
                    {" "}
                    / {item.limit === null ? t("settings.unlimited") : item.limit.toLocaleString(locale)}
                  </span>
                </p>
                <p className="mt-1 text-xs text-platforma-subtle">{item.period_kind === "month" && item.period_start ? t("settings.usageMonth", { month: new Date(item.period_start).toLocaleDateString(locale, { month: "long", year: "numeric", timeZone: "UTC" }) }) : t("settings.usageCurrent")}</p>
                {item.limit !== null ? <div className="mt-3 h-2 rounded-full bg-surface-card" role="progressbar" aria-label={formatMetric(item.metric, t)} aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent}>
                  <div
                    className="h-2 rounded-full bg-ai-gradient"
                    style={{ width: `${percent}%` }}
                  />
                </div> : null}
                {item.limit !== null && item.value >= item.limit ? (
                  <p className="mt-2 text-xs font-semibold text-platforma-danger">
                    {t("settings.limitReached")}
                  </p>
                ) : null}
                {"remaining" in item && item.remaining !== null ? (
                  <p className="mt-2 text-xs font-semibold text-platforma-subtle">
                    {t("settings.remaining", { count: item.remaining })}
                  </p>
                ) : null}
              </div>
            );
          })}
          {!isLoading && !items.length ? (
            <p className="text-sm text-platforma-subtle">{t("settings.noUsage")}</p>
          ) : null}
        </div>}
      </CardBody>
    </Card>
  );
}

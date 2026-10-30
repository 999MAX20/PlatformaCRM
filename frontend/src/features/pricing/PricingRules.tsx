import { formatMoney } from "./pricingPresentation";
import { usePricingRules } from "./usePricingRules";

import { PauseCircle, PlayCircle, TrendingDown } from "lucide-react";

import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";

import { LoadingState } from "../../components/ui/StateViews";
import { Select } from "../../components/ui/Select";

import { useI18n } from "../../lib/i18n";

type Props = {
  t: ReturnType<typeof useI18n>["t"];
  bulkRuleStatus: ReturnType<typeof usePricingRules>["bulkRuleStatus"];
  setBulkRuleStatus: ReturnType<typeof usePricingRules>["setBulkRuleStatus"];
  bulkRuleMinPrice: ReturnType<typeof usePricingRules>["bulkRuleMinPrice"];
  setBulkRuleMinPrice: ReturnType<
    typeof usePricingRules
  >["setBulkRuleMinPrice"];
  bulkRuleStepAmount: ReturnType<typeof usePricingRules>["bulkRuleStepAmount"];
  setBulkRuleStepAmount: ReturnType<
    typeof usePricingRules
  >["setBulkRuleStepAmount"];
  bulkRuleMaxChanges: ReturnType<typeof usePricingRules>["bulkRuleMaxChanges"];
  setBulkRuleMaxChanges: ReturnType<
    typeof usePricingRules
  >["setBulkRuleMaxChanges"];
  canManage: boolean;
  selectedRuleIds: ReturnType<typeof usePricingRules>["selectedRuleIds"];
  bulkRuleDisableAutopilot: ReturnType<
    typeof usePricingRules
  >["bulkRuleDisableAutopilot"];
  bulkUpdateRules: ReturnType<typeof usePricingRules>["bulkUpdateRules"];
  setBulkRuleDisableAutopilot: ReturnType<
    typeof usePricingRules
  >["setBulkRuleDisableAutopilot"];
  rulesQuery: ReturnType<typeof usePricingRules>["rulesQuery"];
  rules: ReturnType<typeof usePricingRules>["rules"];
  latestRecommendations: ReturnType<
    typeof usePricingRules
  >["latestRecommendations"];
  latestOffers: ReturnType<typeof usePricingRules>["latestOffers"];
  setSelectedRuleIds: ReturnType<typeof usePricingRules>["setSelectedRuleIds"];
  competitorPrices: ReturnType<typeof usePricingRules>["competitorPrices"];
  setCompetitorPrices: ReturnType<
    typeof usePricingRules
  >["setCompetitorPrices"];
  collectOffers: ReturnType<typeof usePricingRules>["collectOffers"];
  recommend: ReturnType<typeof usePricingRules>["recommend"];
  apply: ReturnType<typeof usePricingRules>["apply"];
  disableAutopilot: ReturnType<typeof usePricingRules>["disableAutopilot"];
  enableAutopilot: ReturnType<typeof usePricingRules>["enableAutopilot"];
};
export function PricingRules({
  t,
  bulkRuleStatus,
  setBulkRuleStatus,
  bulkRuleMinPrice,
  setBulkRuleMinPrice,
  bulkRuleStepAmount,
  setBulkRuleStepAmount,
  bulkRuleMaxChanges,
  setBulkRuleMaxChanges,
  canManage,
  selectedRuleIds,
  bulkRuleDisableAutopilot,
  bulkUpdateRules,
  setBulkRuleDisableAutopilot,
  rulesQuery,
  rules,
  latestRecommendations,
  latestOffers,
  setSelectedRuleIds,
  competitorPrices,
  setCompetitorPrices,
  collectOffers,
  recommend,
  apply,
  disableAutopilot,
  enableAutopilot,
}: Props) {
  return (
    <section className="rounded-[2rem] border border-platforma-border bg-white p-5 shadow-soft">
      <h2 className="text-lg font-black text-midnight">{t("pricing.rules")}</h2>
      <div className="mt-4 rounded-2xl border border-platforma-border bg-surface-muted p-4">
        <div className="grid gap-3 md:grid-cols-[1fr_1fr_1fr_1fr_auto]">
          <Select
            label={t("pricing.status")}
            value={bulkRuleStatus}
            onChange={(event) => setBulkRuleStatus(event.target.value)}
            options={[
              { value: "", label: t("pricing.doNotChange") },
              { value: "active", label: t("status.active") },
              { value: "paused", label: t("status.paused") },
              { value: "archived", label: t("status.archived") },
            ]}
          />
          <Input
            label={t("pricing.newMinPrice")}
            value={bulkRuleMinPrice}
            onChange={(event) => setBulkRuleMinPrice(event.target.value)}
            type="number"
          />
          <Input
            label={t("pricing.newStep")}
            value={bulkRuleStepAmount}
            onChange={(event) => setBulkRuleStepAmount(event.target.value)}
            type="number"
          />
          <Input
            label={t("pricing.newLimit")}
            value={bulkRuleMaxChanges}
            onChange={(event) => setBulkRuleMaxChanges(event.target.value)}
            type="number"
          />
          <Button
            className="self-end"
            variant="secondary"
            disabled={
              !canManage ||
              !selectedRuleIds.length ||
              (!bulkRuleStatus &&
                !bulkRuleMinPrice &&
                !bulkRuleStepAmount &&
                !bulkRuleMaxChanges &&
                !bulkRuleDisableAutopilot)
            }
            isLoading={bulkUpdateRules.isPending}
            onClick={() => bulkUpdateRules.mutate()}
          >
            {t("pricing.updateSelected", { count: selectedRuleIds.length })}
          </Button>
        </div>
        <label className="mt-3 flex items-center gap-2 text-sm font-bold text-platforma-subtle">
          <input
            className="h-4 w-4 rounded-sm border-platforma-control"
            type="checkbox"
            checked={bulkRuleDisableAutopilot}
            onChange={(event) =>
              setBulkRuleDisableAutopilot(event.target.checked)
            }
          />
          {t("pricing.disableAutopilotSelected")}
        </label>
      </div>
      {rulesQuery.isLoading ? <LoadingState /> : null}
      <div className="mt-4 grid gap-3">
        {rules.map((rule) => {
          const latest = latestRecommendations.get(String(rule.id));
          const latestOffer = latestOffers.get(String(rule.id));
          return (
            <article
              key={rule.id}
              className="rounded-2xl border border-platforma-border bg-surface-muted p-4"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <input
                    className="mt-1 h-5 w-5 rounded-sm border-platforma-control"
                    type="checkbox"
                    checked={selectedRuleIds.includes(String(rule.id))}
                    onChange={(event) => {
                      const id = String(rule.id);
                      setSelectedRuleIds(
                        event.target.checked
                          ? [...selectedRuleIds, id]
                          : selectedRuleIds.filter((value) => value !== id),
                      );
                    }}
                    aria-label={t("pricing.selectRule", {
                      name: rule.product_name || rule.product_sku,
                    })}
                  />
                  <div>
                    <p className="text-base font-black text-midnight">
                      {rule.product_name || rule.product_sku}
                    </p>
                    <p className="mt-1 text-sm font-semibold text-platforma-faint">
                      {t("pricing.ruleMeta", {
                        sku: rule.product_sku,
                        current: formatMoney(rule.current_price),
                        min: formatMoney(rule.min_price),
                      })}
                    </p>
                  </div>
                </div>
                <span className="rounded-full bg-[var(--platforma-success-soft)] px-3 py-1 text-xs font-black text-platforma-success">
                  {rule.mode} · {rule.status}
                </span>
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-[1fr_auto_auto_auto]">
                <Input
                  label={t("pricing.manualCompetitorPrice")}
                  value={competitorPrices[String(rule.id)] || ""}
                  onChange={(event) =>
                    setCompetitorPrices({
                      ...competitorPrices,
                      [String(rule.id)]: event.target.value,
                    })
                  }
                  type="number"
                />
                <Button
                  className="self-end"
                  variant="secondary"
                  disabled={!canManage}
                  isLoading={collectOffers.isPending}
                  onClick={() => collectOffers.mutate(rule)}
                >
                  {t("pricing.collectPrices")}
                </Button>
                <Button
                  className="self-end"
                  variant="secondary"
                  disabled={!canManage}
                  isLoading={recommend.isPending}
                  onClick={() => recommend.mutate(rule)}
                >
                  <TrendingDown size={16} /> {t("pricing.calculate")}
                </Button>
                <Button
                  className="self-end"
                  disabled={
                    !canManage || !latest || latest.status !== "proposed"
                  }
                  isLoading={apply.isPending}
                  onClick={() => latest && apply.mutate(latest)}
                >
                  {t("pricing.apply")}
                </Button>
              </div>
              {latestOffer ? (
                <div className="mt-3 rounded-2xl bg-white px-3 py-2 text-sm font-semibold text-platforma-subtle">
                  {t("pricing.foundPrice", {
                    price: formatMoney(latestOffer.price),
                    competitor:
                      latestOffer.competitor_name || t("pricing.competitor"),
                    position: latestOffer.position || 1,
                  })}
                </div>
              ) : null}
              {latest ? (
                <div className="mt-3 rounded-2xl bg-white px-3 py-2 text-sm font-semibold text-platforma-subtle">
                  {t("pricing.recommendationLine", {
                    price: formatMoney(latest.target_price),
                    reason: latest.reason,
                    status: latest.status,
                  })}
                </div>
              ) : null}
              <div className="mt-4 rounded-2xl border border-platforma-border bg-white p-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-black text-midnight">
                      {t("pricing.autopilot")}
                    </p>
                    <p className="mt-1 text-sm font-semibold text-platforma-faint">
                      {rule.mode === "autopilot"
                        ? t("pricing.autopilotEnabledText")
                        : t("pricing.autopilotCheckText")}
                    </p>
                  </div>
                  {rule.mode === "autopilot" ? (
                    <Button
                      variant="warning"
                      disabled={!canManage}
                      isLoading={disableAutopilot.isPending}
                      onClick={() => disableAutopilot.mutate(rule)}
                    >
                      <PauseCircle size={16} /> {t("pricing.stop")}
                    </Button>
                  ) : (
                    <Button
                      disabled={
                        !canManage ||
                        !latestOffer ||
                        Number(rule.min_price) <= 0 ||
                        rule.max_changes_per_day <= 0
                      }
                      isLoading={enableAutopilot.isPending}
                      onClick={() => enableAutopilot.mutate(rule)}
                    >
                      <PlayCircle size={16} /> {t("pricing.enableAutopilot")}
                    </Button>
                  )}
                </div>
                <div className="mt-3 grid gap-2 text-sm font-semibold text-platforma-subtle md:grid-cols-4">
                  <span className="rounded-xl bg-surface-muted px-3 py-2">
                    {t("pricing.minPriceValue", {
                      price: formatMoney(rule.min_price),
                    })}
                  </span>
                  <span className="rounded-xl bg-surface-muted px-3 py-2">
                    {t("pricing.limitValue", {
                      count: rule.max_changes_per_day,
                    })}
                  </span>
                  <span className="rounded-xl bg-surface-muted px-3 py-2">
                    {t("pricing.monitoringValue", {
                      status: latestOffer
                        ? t("pricing.priceFound")
                        : t("pricing.collectPricesFirst"),
                    })}
                  </span>
                  <span className="rounded-xl bg-surface-muted px-3 py-2">
                    {t("pricing.kaspiWriteFlag")}
                  </span>
                </div>
                {rule.autopilot_confirmed_at ? (
                  <p className="mt-2 text-xs font-bold text-platforma-success">
                    {t("pricing.confirmedAt", {
                      date: new Date(
                        rule.autopilot_confirmed_at,
                      ).toLocaleString("ru-KZ"),
                    })}
                  </p>
                ) : null}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

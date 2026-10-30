import { formatMoney } from "./pricingPresentation";

import { usePricingCatalog } from "./usePricingCatalog";

import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";

import { LoadingState } from "../../components/ui/StateViews";
import { Select } from "../../components/ui/Select";
import { useActiveBusiness } from "../../hooks/useBusiness";

import { useI18n } from "../../lib/i18n";

type Props = {
  t: ReturnType<typeof useI18n>["t"];
  canManage: boolean;
  business: ReturnType<typeof useActiveBusiness>["business"];
  syncCatalog: ReturnType<typeof usePricingCatalog>["syncCatalog"];
  bulkMinPrice: ReturnType<typeof usePricingCatalog>["bulkMinPrice"];
  setBulkMinPrice: ReturnType<typeof usePricingCatalog>["setBulkMinPrice"];
  bulkStepAmount: ReturnType<typeof usePricingCatalog>["bulkStepAmount"];
  setBulkStepAmount: ReturnType<typeof usePricingCatalog>["setBulkStepAmount"];
  bulkMaxChanges: ReturnType<typeof usePricingCatalog>["bulkMaxChanges"];
  setBulkMaxChanges: ReturnType<typeof usePricingCatalog>["setBulkMaxChanges"];
  selectedCatalogIds: ReturnType<
    typeof usePricingCatalog
  >["selectedCatalogIds"];
  bulkCreateRules: ReturnType<typeof usePricingCatalog>["bulkCreateRules"];
  catalogSearch: ReturnType<typeof usePricingCatalog>["catalogSearch"];
  setCatalogSearch: ReturnType<typeof usePricingCatalog>["setCatalogSearch"];
  catalogSource: ReturnType<typeof usePricingCatalog>["catalogSource"];
  setCatalogSource: ReturnType<typeof usePricingCatalog>["setCatalogSource"];
  catalogSources: ReturnType<typeof usePricingCatalog>["catalogSources"];
  catalogRuleState: ReturnType<typeof usePricingCatalog>["catalogRuleState"];
  setCatalogRuleState: ReturnType<
    typeof usePricingCatalog
  >["setCatalogRuleState"];
  catalogQuery: ReturnType<typeof usePricingCatalog>["catalogQuery"];
  catalogItems: ReturnType<typeof usePricingCatalog>["catalogItems"];
  setSelectedCatalogIds: ReturnType<
    typeof usePricingCatalog
  >["setSelectedCatalogIds"];
  catalogMinPrices: ReturnType<typeof usePricingCatalog>["catalogMinPrices"];
  setCatalogMinPrices: ReturnType<
    typeof usePricingCatalog
  >["setCatalogMinPrices"];
  createRuleFromCatalog: ReturnType<
    typeof usePricingCatalog
  >["createRuleFromCatalog"];
};
export function PricingCatalog({
  t,
  canManage,
  business,
  syncCatalog,
  bulkMinPrice,
  setBulkMinPrice,
  bulkStepAmount,
  setBulkStepAmount,
  bulkMaxChanges,
  setBulkMaxChanges,
  selectedCatalogIds,
  bulkCreateRules,
  catalogSearch,
  setCatalogSearch,
  catalogSource,
  setCatalogSource,
  catalogSources,
  catalogRuleState,
  setCatalogRuleState,
  catalogQuery,
  catalogItems,
  setSelectedCatalogIds,
  catalogMinPrices,
  setCatalogMinPrices,
  createRuleFromCatalog,
}: Props) {
  return (
    <section className="rounded-[2rem] border border-platforma-border bg-white p-5 shadow-soft">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-black text-midnight">
            {t("pricing.catalogTitle")}
          </h2>
          <p className="mt-1 text-sm font-semibold text-platforma-faint">
            {t("pricing.catalogText")}
          </p>
        </div>
        <Button
          variant="secondary"
          disabled={!canManage || !business?.id}
          isLoading={syncCatalog.isPending}
          onClick={() => syncCatalog.mutate()}
        >
          {t("pricing.refreshCatalog")}
        </Button>
      </div>
      <div className="mt-4 rounded-2xl border border-platforma-border bg-surface-muted p-4">
        <div className="grid gap-3 md:grid-cols-[1fr_1fr_1fr_auto]">
          <Input
            label={t("pricing.bulkMinPrice")}
            value={bulkMinPrice}
            onChange={(event) => setBulkMinPrice(event.target.value)}
            type="number"
          />
          <Input
            label={t("pricing.step")}
            value={bulkStepAmount}
            onChange={(event) => setBulkStepAmount(event.target.value)}
            type="number"
          />
          <Input
            label={t("pricing.dailyLimit")}
            value={bulkMaxChanges}
            onChange={(event) => setBulkMaxChanges(event.target.value)}
            type="number"
          />
          <Button
            className="self-end"
            disabled={!canManage || !selectedCatalogIds.length || !bulkMinPrice}
            isLoading={bulkCreateRules.isPending}
            onClick={() => bulkCreateRules.mutate()}
          >
            {t("pricing.createForSelected", {
              count: selectedCatalogIds.length,
            })}
          </Button>
        </div>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <Input
          data-testid="pricing-catalog-search-input"
          label={t("common.search")}
          value={catalogSearch}
          onChange={(event) => setCatalogSearch(event.target.value)}
          placeholder={t("pricing.searchPlaceholder")}
        />
        <Select
          label={t("pricing.source")}
          value={catalogSource}
          onChange={(event) => setCatalogSource(event.target.value)}
          options={[
            { value: "", label: t("pricing.allSources") },
            ...catalogSources.map((source) => ({
              value: source,
              label: source,
            })),
          ]}
        />
        <Select
          label={t("pricing.status")}
          value={catalogRuleState}
          onChange={(event) => setCatalogRuleState(event.target.value)}
          options={[
            { value: "", label: t("pricing.allProducts") },
            { value: "missing", label: t("pricing.withoutRule") },
            { value: "connected", label: t("pricing.connectedProducts") },
          ]}
        />
      </div>
      {catalogQuery.isLoading ? <LoadingState /> : null}
      <div className="mt-4 grid gap-3">
        {catalogItems.map((item) => (
          <article
            key={item.id}
            className="rounded-2xl border border-platforma-border bg-surface-muted p-4"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <input
                  className="mt-1 h-5 w-5 rounded-sm border-platforma-control"
                  type="checkbox"
                  checked={selectedCatalogIds.includes(String(item.id))}
                  disabled={Boolean(item.rule_id)}
                  onChange={(event) => {
                    const id = String(item.id);
                    setSelectedCatalogIds(
                      event.target.checked
                        ? [...selectedCatalogIds, id]
                        : selectedCatalogIds.filter((value) => value !== id),
                    );
                  }}
                  aria-label={t("pricing.selectItem", {
                    name: item.name || item.sku,
                  })}
                />
                <div>
                  <p className="text-base font-black text-midnight">
                    {item.name || item.sku}
                  </p>
                  <p className="mt-1 text-sm font-semibold text-platforma-faint">
                    {t("pricing.catalogItemMeta", {
                      source: item.source,
                      sku: item.sku,
                      price: formatMoney(item.current_price),
                      stock: item.stock_quantity || t("pricing.noData"),
                    })}
                  </p>
                </div>
              </div>
              <span className="rounded-full bg-white px-3 py-1 text-xs font-black text-platforma-subtle">
                {item.rule_id
                  ? t("pricing.ruleMode", { mode: item.rule_mode || "" })
                  : t("pricing.notConnected")}
              </span>
            </div>
            <div className="mt-3 grid gap-3 md:grid-cols-[1fr_auto]">
              <Input
                label={t("pricing.minPrice")}
                value={catalogMinPrices[String(item.id)] || ""}
                onChange={(event) =>
                  setCatalogMinPrices({
                    ...catalogMinPrices,
                    [String(item.id)]: event.target.value,
                  })
                }
                type="number"
                disabled={Boolean(item.rule_id)}
              />
              <Button
                className="self-end"
                disabled={
                  !canManage ||
                  Boolean(item.rule_id) ||
                  !catalogMinPrices[String(item.id)]
                }
                isLoading={createRuleFromCatalog.isPending}
                onClick={() => createRuleFromCatalog.mutate(item)}
              >
                {t("pricing.createRule")}
              </Button>
            </div>
          </article>
        ))}
      </div>
      {!catalogQuery.isLoading && catalogItems.length === 0 ? (
        <div className="mt-4 rounded-2xl bg-surface-muted px-4 py-3 text-sm font-semibold text-platforma-faint">
          {t("pricing.emptyCatalog")}
        </div>
      ) : null}
    </section>
  );
}

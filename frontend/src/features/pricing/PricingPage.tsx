import { PricingHistory } from "./PricingHistory";
import { PricingRules } from "./PricingRules";
import { PricingRuleForm } from "./PricingRuleForm";
import { PricingCatalog } from "./PricingCatalog";
import { PricingSafetyPanel } from "./PricingSafetyPanel";

import { usePricingRules } from "./usePricingRules";
import { usePricingCatalog } from "./usePricingCatalog";
import { usePricingSafety } from "./usePricingSafety";
import { usePricingChangeLogs } from "./usePricingChangeLogs";

import { getApiErrorMessage } from "../../api/client";

import { PageHeader } from "../../components/ui/PageHeader";
import { ErrorState } from "../../components/ui/StateViews";

import { useActiveBusiness } from "../../hooks/useBusiness";

import { useAuth } from "../auth/AuthProvider";
import { hasPermission } from "../../lib/permissions";
import { useI18n } from "../../lib/i18n";

export function PricingPage() {
  const { t } = useI18n();

  const { user } = useAuth();
  const { business } = useActiveBusiness();
  const canManage = hasPermission(user, business?.id, "integrations", "manage");
  const {
    form,
    setForm,
    competitorPrices,
    setCompetitorPrices,
    selectedRuleIds,
    setSelectedRuleIds,
    bulkRuleStatus,
    setBulkRuleStatus,
    bulkRuleMinPrice,
    setBulkRuleMinPrice,
    bulkRuleStepAmount,
    setBulkRuleStepAmount,
    bulkRuleMaxChanges,
    setBulkRuleMaxChanges,
    bulkRuleDisableAutopilot,
    setBulkRuleDisableAutopilot,
    rulesQuery,
    recommendationsQuery,
    competitorOffersQuery,
    createRule,
    recommend,
    collectOffers,
    apply,
    enableAutopilot,
    disableAutopilot,
    bulkUpdateRules,
    rules,
    latestRecommendations,
    latestOffers,
  } = usePricingRules(business);
  const {
    catalogMinPrices,
    setCatalogMinPrices,
    selectedCatalogIds,
    setSelectedCatalogIds,
    bulkMinPrice,
    setBulkMinPrice,
    bulkStepAmount,
    setBulkStepAmount,
    bulkMaxChanges,
    setBulkMaxChanges,
    catalogSearch,
    setCatalogSearch,
    catalogSource,
    setCatalogSource,
    catalogRuleState,
    setCatalogRuleState,
    catalogQuery,
    syncCatalog,
    createRuleFromCatalog,
    bulkCreateRules,
    catalogItems,
    catalogSources,
  } = usePricingCatalog(business, form);
  const {
    controlQuery,
    alertsQuery,
    emergencyStop,
    resumePricing,
    alerts,
    control,
  } = usePricingSafety(business);
  const {
    changeSearch,
    setChangeSearch,
    changeStatus,
    setChangeStatus,
    changeLogsQuery,
    changeLogs,
  } = usePricingChangeLogs(business);

  const error =
    rulesQuery.error ||
    recommendationsQuery.error ||
    competitorOffersQuery.error ||
    catalogQuery.error ||
    controlQuery.error ||
    alertsQuery.error ||
    changeLogsQuery.error ||
    createRule.error ||
    syncCatalog.error ||
    createRuleFromCatalog.error ||
    bulkCreateRules.error ||
    recommend.error ||
    collectOffers.error ||
    apply.error ||
    enableAutopilot.error ||
    disableAutopilot.error ||
    bulkUpdateRules.error ||
    emergencyStop.error ||
    resumePricing.error;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Kaspi Pricing"
        description={t("pricing.description")}
      />

      {error ? (
        <ErrorState error={error} message={getApiErrorMessage(error)} />
      ) : null}

      <PricingSafetyPanel
        control={control}
        t={t}
        alerts={alerts}
        canManage={canManage}
        resumePricing={resumePricing}
        emergencyStop={emergencyStop}
      />

      <PricingCatalog
        t={t}
        canManage={canManage}
        business={business}
        syncCatalog={syncCatalog}
        bulkMinPrice={bulkMinPrice}
        setBulkMinPrice={setBulkMinPrice}
        bulkStepAmount={bulkStepAmount}
        setBulkStepAmount={setBulkStepAmount}
        bulkMaxChanges={bulkMaxChanges}
        setBulkMaxChanges={setBulkMaxChanges}
        selectedCatalogIds={selectedCatalogIds}
        bulkCreateRules={bulkCreateRules}
        catalogSearch={catalogSearch}
        setCatalogSearch={setCatalogSearch}
        catalogSource={catalogSource}
        setCatalogSource={setCatalogSource}
        catalogSources={catalogSources}
        catalogRuleState={catalogRuleState}
        setCatalogRuleState={setCatalogRuleState}
        catalogQuery={catalogQuery}
        catalogItems={catalogItems}
        setSelectedCatalogIds={setSelectedCatalogIds}
        catalogMinPrices={catalogMinPrices}
        setCatalogMinPrices={setCatalogMinPrices}
        createRuleFromCatalog={createRuleFromCatalog}
      />

      <PricingRuleForm
        t={t}
        form={form}
        setForm={setForm}
        canManage={canManage}
        createRule={createRule}
      />

      <PricingRules
        t={t}
        bulkRuleStatus={bulkRuleStatus}
        setBulkRuleStatus={setBulkRuleStatus}
        bulkRuleMinPrice={bulkRuleMinPrice}
        setBulkRuleMinPrice={setBulkRuleMinPrice}
        bulkRuleStepAmount={bulkRuleStepAmount}
        setBulkRuleStepAmount={setBulkRuleStepAmount}
        bulkRuleMaxChanges={bulkRuleMaxChanges}
        setBulkRuleMaxChanges={setBulkRuleMaxChanges}
        canManage={canManage}
        selectedRuleIds={selectedRuleIds}
        bulkRuleDisableAutopilot={bulkRuleDisableAutopilot}
        bulkUpdateRules={bulkUpdateRules}
        setBulkRuleDisableAutopilot={setBulkRuleDisableAutopilot}
        rulesQuery={rulesQuery}
        rules={rules}
        latestRecommendations={latestRecommendations}
        latestOffers={latestOffers}
        setSelectedRuleIds={setSelectedRuleIds}
        competitorPrices={competitorPrices}
        setCompetitorPrices={setCompetitorPrices}
        collectOffers={collectOffers}
        recommend={recommend}
        apply={apply}
        disableAutopilot={disableAutopilot}
        enableAutopilot={enableAutopilot}
      />

      <PricingHistory
        t={t}
        changeLogs={changeLogs}
        changeSearch={changeSearch}
        setChangeSearch={setChangeSearch}
        changeStatus={changeStatus}
        setChangeStatus={setChangeStatus}
        changeLogsQuery={changeLogsQuery}
      />
    </div>
  );
}

import type { Dispatch, SetStateAction } from "react";

import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { Card, CardBody } from "../../../components/ui/Card";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import type { Id, Subscription, SubscriptionPlan } from "../../../types";
import type { Translate } from "../settingsUtils";

type BillingSettingsForm = {
  billing_email: string;
  payment_method: string;
  invoice_name: string;
  invoice_tax_id: string;
  invoice_address: string;
};

type BillingSectionProps = {
  canManageBilling: boolean;
  className: string;
  currentPlan?: SubscriptionPlan | null;
  error: unknown;
  hasSubscription: boolean;
  isPlanChangePending: boolean;
  isSavingBillingSettings: boolean;
  onRequestPlanChange: (plan: Id) => void;
  onSaveBillingSettings: () => void;
  onRetry: () => void;
  plans: SubscriptionPlan[];
  selectedPlanId: string;
  setBillingSettingsForm: Dispatch<SetStateAction<BillingSettingsForm>>;
  setSelectedPlanId: (planId: string) => void;
  subscription?: Subscription | null;
  subscriptionIsLoading: boolean;
  billingSettingsForm: BillingSettingsForm;
  t: Translate;
};

export function BillingSection({
  billingSettingsForm,
  canManageBilling,
  className,
  currentPlan,
  error,
  hasSubscription,
  isPlanChangePending,
  isSavingBillingSettings,
  onRequestPlanChange,
  onSaveBillingSettings,
  onRetry,
  plans,
  selectedPlanId,
  setBillingSettingsForm,
  setSelectedPlanId,
  subscription,
  subscriptionIsLoading,
  t,
}: BillingSectionProps) {
  if (subscriptionIsLoading) return <Card id="billing" className={className}><CardBody><LoadingState /></CardBody></Card>;

  return (
    <Card id="billing" className={className}>
      <CardBody>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-brand-700">
              {t("settings.currentPlan")}
            </p>
            <h2 className="mt-2 text-2xl font-semibold text-platforma-text">
              {currentPlan?.name || t("settings.noPlan")}
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-platforma-subtle">
              {hasSubscription
                ? t("settings.billingRecordStatus", { status: t(`settings.subscriptionStatus.${subscription?.status}`) })
                : t("settings.billingNoSubscription")}
            </p>
            {subscription?.requested_plan ? (
              <p className="mt-2 text-sm font-bold text-platforma-warning">
                {t("settings.savedPlanPreference", { name: plans.find((plan) => String(plan.id) === String(subscription.requested_plan))?.name || `#${subscription.requested_plan}` })}
              </p>
            ) : null}
          </div>

        </div>
        <p className="mt-2 text-sm text-platforma-subtle">{t("settings.billingMetadataOnly")}</p>
        {error ? (
          <div className="mt-4">
            <ErrorState error={error} message={getApiErrorMessage(error)} action={<Button type="button" variant="secondary" onClick={onRetry}>{t("common.retry")}</Button>} />
          </div>
        ) : null}
        {subscription ? <div className="mt-5 grid gap-4 xl:grid-cols-[1fr_0.8fr]">
          <form
            className="rounded-card border border-platforma-border bg-surface-muted p-4"
            onSubmit={(event) => {
              event.preventDefault();
              onSaveBillingSettings();
            }}
          >
            <h3 className="font-bold text-platforma-text">
              {t("settings.billingPaymentsTitle")}
            </h3>
            <fieldset disabled={!canManageBilling || isSavingBillingSettings} className="mt-4 grid gap-3 sm:grid-cols-2">
              <Input
                type="email" label={t("settings.billingEmail")}
                value={billingSettingsForm.billing_email}
                onChange={(event) =>
                  setBillingSettingsForm({
                    ...billingSettingsForm,
                    billing_email: event.target.value,
                  })
                }
              />
              <Input label={t("settings.paymentMethodReference")} readOnly
                value={billingSettingsForm.payment_method ? (["invoice", "card", "bank_transfer"].includes(billingSettingsForm.payment_method) ? t(`settings.paymentMethod.${billingSettingsForm.payment_method === "bank_transfer" ? "bankTransfer" : billingSettingsForm.payment_method}`) : billingSettingsForm.payment_method) : t("settings.paymentMethod.empty")} />
              <Input
                label={t("settings.invoiceName")}
                value={billingSettingsForm.invoice_name}
                onChange={(event) =>
                  setBillingSettingsForm({
                    ...billingSettingsForm,
                    invoice_name: event.target.value,
                  })
                }
              />
              <Input
                label={t("settings.invoiceTaxId")}
                value={billingSettingsForm.invoice_tax_id}
                onChange={(event) =>
                  setBillingSettingsForm({
                    ...billingSettingsForm,
                    invoice_tax_id: event.target.value,
                  })
                }
              />
              <Input
                className="sm:col-span-2"
                label={t("settings.invoiceAddress")}
                value={billingSettingsForm.invoice_address}
                onChange={(event) =>
                  setBillingSettingsForm({
                    ...billingSettingsForm,
                    invoice_address: event.target.value,
                  })
                }
              />
            </fieldset>
            <div className="mt-4">
              <Button
                type="submit"
                disabled={!canManageBilling || !subscription}
                isLoading={isSavingBillingSettings}
              >
                {t("settings.saveBilling")}
              </Button>
            </div>
          </form>
          <div className="rounded-card border border-platforma-border bg-surface-card p-4">
            <h3 className="font-bold text-platforma-text">
              {t("settings.planPreferenceTitle")}
            </h3>
            <p className="mt-1 text-sm leading-6 text-platforma-subtle">
              {t("settings.planPreferenceText")}
            </p>
            <div className="mt-4 grid gap-3">
              <Select
                disabled={!canManageBilling || isPlanChangePending || !plans.length} label={t("settings.newPlan")}
                value={selectedPlanId}
                onChange={(event) => setSelectedPlanId(event.target.value)}
                options={plans.map((plan) => ({
                  value: String(plan.id),
                  label: plan.name,
                }))}
              />
              <Button
                type="button"
                disabled={
                  !canManageBilling ||
                  !selectedPlanId ||
                  !plans.some((plan) => String(plan.id) === selectedPlanId) ||
                  selectedPlanId === String(subscription.requested_plan || currentPlan?.id || "")
                }
                onClick={() => onRequestPlanChange(Number(selectedPlanId))}
                isLoading={isPlanChangePending}
              >
                {t("settings.savePlanPreference")}
              </Button>
            </div>
          </div>
        </div> : null}
      </CardBody>
    </Card>
  );
}

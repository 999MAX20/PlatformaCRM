import { getApiFieldErrors } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import { SettingsFeedback, SettingsReference, SettingsSaveBar, SettingsSection } from "../components/SettingsLayout";
import { SettingsQueryState } from "../components/SettingsQueryState";
import type { SettingsModel } from "../useSettingsModel";

export function BillingSection({ model }: { model: SettingsModel; }) {
  const { t, activeSettingsSection, subscription, plans, currentPlan, canManageBilling, billingSettingsForm, setBillingSettingsForm, billingSettingsMutation, planChangeMutation, selectedPlanId, setSelectedPlanId } = model;
  const record = subscription.data;
  const details = record?.invoice_details_json || {};
  const errors = getApiFieldErrors(billingSettingsMutation.error);
  const pending = billingSettingsMutation.isPending || planChangeMutation.isPending;
  const hasFieldErrors = Boolean(errors.billing_email?.length);
  const original = { billing_email: record?.billing_email || "", payment_method: record?.payment_method || "", invoice_name: String(details.name || ""), invoice_tax_id: String(details.tax_id || ""), invoice_address: String(details.address || "") };
  const dirty = Object.keys(original).some(key => original[key as keyof typeof original] !== billingSettingsForm[key as keyof typeof original]);
  function field(name: keyof typeof billingSettingsForm) {
    return { value: billingSettingsForm[name], onChange: (event: React.ChangeEvent<HTMLInputElement>) => { setBillingSettingsForm(current => ({ ...current, [name]: event.target.value })); billingSettingsMutation.reset(); } };
  }
  return <SettingsSection id="billing" active={activeSettingsSection} title={t("settings.section.billing")}>
    <div className="space-y-5 p-4 sm:p-5">
      <SettingsQueryState queries={[subscription, plans]} />
      {subscription.isSuccess && !record && <p className="text-sm text-platforma-subtle">{t("settings.billingNoSubscription")}</p>}
      {record && !subscription.isError && <>
        <div className="flex flex-wrap items-start justify-between gap-3 border-b border-platforma-border pb-5">
          <div><p className="text-xs text-platforma-subtle">{t("settings.currentPlan")}</p><h2 className="mt-1 text-base font-bold">{currentPlan?.name || t("settings.noPlan")}</h2></div>
          <p className="text-sm text-platforma-subtle">{t("settings.billingRecordStatus", { status: t(`settings.subscriptionStatus.${record.status}`) })}</p>
        </div>
        <div className="space-y-3">
          <h2 className="text-base font-bold">{t("settings.planPreferenceTitle")}</h2>
          <p className="max-w-3xl text-sm leading-6 text-platforma-subtle">{t("settings.planPreferenceText")}</p>
          <div className="flex flex-wrap items-end gap-3">
            <div className="min-w-0 flex-1 sm:max-w-md"><Select label={t("settings.newPlan")} value={selectedPlanId} disabled={!canManageBilling || pending || !plans.data?.length || plans.isError}
              onChange={event => { setSelectedPlanId(event.target.value); planChangeMutation.reset(); }}
              options={(plans.data || []).map(plan => ({ value: String(plan.id), label: plan.name }))} /></div>
            <Button type="button" variant="secondary" disabled={!canManageBilling || pending || !selectedPlanId || !plans.data?.some(plan => String(plan.id) === selectedPlanId) || selectedPlanId === String(record.requested_plan || currentPlan?.id || "")}
              isLoading={planChangeMutation.isPending} onClick={() => planChangeMutation.mutate(Number(selectedPlanId))}>{t("settings.savePlanPreference")}</Button>
          </div>
          <SettingsFeedback error={planChangeMutation.error} saved={planChangeMutation.isSuccess} />
          {record.requested_plan && <p className="text-sm text-platforma-subtle">{t("settings.savedPlanPreference", { name: plans.data?.find(plan => String(plan.id) === String(record.requested_plan))?.name || "#" + record.requested_plan })}</p>}
        </div>
        <form id="settings-billing-form" onSubmit={event => { event.preventDefault(); billingSettingsMutation.mutate(undefined, { onError: () => window.requestAnimationFrame(() => document.querySelector<HTMLElement>('#settings-billing-form [aria-invalid="true"]')?.focus()) }); }}
          className="space-y-4 border-t border-platforma-border pt-5">
          <h2 className="text-base font-bold">{t("settings.billingPaymentsTitle")}</h2>
          <fieldset disabled={!canManageBilling || pending} className="grid gap-3 sm:grid-cols-2">
            <Input label={t("settings.billingEmail")} type="email" error={errors.billing_email?.join(" ")} {...field("billing_email")} />
            <Input label={t("settings.invoiceName")} {...field("invoice_name")} />
            <Input label={t("settings.invoiceTaxId")} {...field("invoice_tax_id")} />
            <Input label={t("settings.invoiceAddress")} {...field("invoice_address")} />
          </fieldset>
        </form>
        <SettingsReference>
          <dl><dt className="text-xs text-platforma-subtle">{t("settings.paymentMethodReference")}</dt><dd className="mt-1 text-sm">{billingSettingsForm.payment_method ? (["invoice", "card", "bank_transfer"].includes(billingSettingsForm.payment_method) ? t(`settings.paymentMethod.${(billingSettingsForm.payment_method === "bank_transfer" ? "bankTransfer" : billingSettingsForm.payment_method)}`) : billingSettingsForm.payment_method) : t("settings.paymentMethod.empty")}</dd></dl>
          <p className="text-xs leading-5 text-platforma-subtle">{t("settings.billingMetadataOnly")}</p>
        </SettingsReference>
      </>}
    </div>
    {record && !subscription.isError && canManageBilling && <SettingsSaveBar feedback={!hasFieldErrors && billingSettingsMutation.error ? <SettingsFeedback error={billingSettingsMutation.error} /> : dirty && !billingSettingsMutation.isSuccess ? <p className="text-sm text-platforma-subtle">{t("settings.redesign.unsaved")}</p> : <SettingsFeedback saved={billingSettingsMutation.isSuccess} />}>
      <Button type="button" variant="secondary" disabled={!dirty || pending} onClick={() => { setBillingSettingsForm(original); billingSettingsMutation.reset(); }}>{t("common.cancel")}</Button>
      <Button type="submit" form="settings-billing-form" disabled={!dirty || pending} isLoading={billingSettingsMutation.isPending}>{t("settings.saveBilling")}</Button>
    </SettingsSaveBar>}
  </SettingsSection>;
}

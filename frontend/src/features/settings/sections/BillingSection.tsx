import { MerchantBilling } from "../../billing/MerchantBilling";
import { SettingsSection } from "../components/SettingsLayout";
import type { SettingsModel } from "../useSettingsModel";

export function BillingSection({ model }: { model: SettingsModel }) {
  return <SettingsSection id="billing" active={model.activeSettingsSection} title={model.t("settings.section.billing")}>
    {model.activeSettingsSection === "billing" && model.business && <MerchantBilling key={model.business.id} business={String(model.business.id)} />}
  </SettingsSection>;
}

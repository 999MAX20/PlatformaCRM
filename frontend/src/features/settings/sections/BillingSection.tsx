import { SettingsSection } from "../components/SettingsLayout";
import type { SettingsModel } from "../useSettingsModel";

export function BillingSection({ model }: { model: SettingsModel }) {
  return <SettingsSection id="billing" active={model.activeSettingsSection} title={model.t("settings.section.billing")}>
    <div className="min-h-24" />
  </SettingsSection>;
}

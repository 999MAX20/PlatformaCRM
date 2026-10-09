import { BusinessSettingsForm } from "../../../components/forms/BusinessSettingsForm";
import { SettingsSection } from "../components/SettingsLayout";
import type { SettingsModel } from "../useSettingsModel";

export function BusinessProfileSection({ model }: { model: SettingsModel; }) {
  return <SettingsSection id="business-profile" active={model.activeSettingsSection} title={model.t("settings.section.business-profile")}>
    <BusinessSettingsForm initial={model.business} onSubmit={payload => model.mutation.mutateAsync(payload)} />
  </SettingsSection>;
}

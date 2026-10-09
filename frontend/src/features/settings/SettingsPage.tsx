import { Navigate, useLocation } from "react-router";
import { ForbiddenState, LoadingState } from "../../components/ui/StateViews";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { SettingsNavigation } from "./components/SettingsNavigation";
import { SettingsQueryState } from "./components/SettingsQueryState";
import { AppointmentMessagesSection } from "./sections/AppointmentMessagesSection";
import { BillingSection } from "./sections/BillingSection";
import { BusinessProfileSection } from "./sections/BusinessProfileSection";
import { CustomFieldsSection } from "./sections/CustomFieldsSection";
import { QuickRepliesSection } from "./sections/QuickRepliesSection";
import { RolesSection } from "./sections/RolesSection";
import { SecuritySection } from "./sections/SecuritySection";
import { TeamSection } from "./sections/TeamSection";
import { UsageSection } from "./sections/UsageSection";
import { useSettingsModel } from "./useSettingsModel";

const sections = [
  ["business-profile", BusinessProfileSection],
  ["team-access", TeamSection],
  ["roles", RolesSection],
  ["security-center", SecuritySection],
  ["appointment-messages", AppointmentMessagesSection],
  ["quick-replies", QuickRepliesSection],
  ["custom-fields", CustomFieldsSection],
  ["billing", BillingSection],
  ["usage", UsageSection],
] as const;

export function SettingsPage() {
  const { hash } = useLocation();
  const businessQuery = useActiveBusiness();
  const { business } = businessQuery;
  if (hash === "#notification-preferences") return <Navigate to="/app/account#notifications" replace />;
  if (!business && businessQuery.isError) return <SettingsQueryState queries={[businessQuery]} />;
  return <BusinessSettingsPage key={business?.id ?? "no-business"} />;
}
function BusinessSettingsPage() {
  const model = useSettingsModel();
  if (model.isLoading) return <LoadingState scope="page" />;
  if (!model.business) return <p className="p-5 text-sm text-platforma-subtle">{model.t("settings.redesign.noBusiness")}</p>;
  if (!model.allowedSettingsSections.length) return <ForbiddenState />;
  return <div data-testid="settings-workspace-ready" className="settings-workspace grid items-start gap-4 lg:grid-cols-[216px_minmax(0,1fr)]">
    <SettingsNavigation activeSettingsSection={model.activeSettingsSection} navigationTitle={model.t("settings.navigationTitle")}
      setActiveSettingsSection={model.setActiveSettingsSection} translatedSettingsGroups={model.translatedSettingsGroups}
      translatedSettingsSections={model.translatedSettingsSections} />
    <div className="min-w-0">
      {sections.map(([id, Section]) => model.allowedSettingsSectionIds.has(id) ? <Section key={id} model={model} /> : null)}
    </div>
  </div>;
}

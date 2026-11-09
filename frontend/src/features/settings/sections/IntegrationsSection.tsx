import { lazy, Suspense } from "react";
import { LoadingState } from "../../../components/ui/StateViews";
import { SettingsSection } from "../components/SettingsLayout";
import type { SettingsModel } from "../useSettingsModel";

const IntegrationsPage = lazy(() => import("../../integrations/IntegrationsPage").then(module => ({ default: module.IntegrationsPage })));

export function IntegrationsSection({ model }: { model: SettingsModel }) {
  if (model.activeSettingsSection !== "integrations") return null;
  return <SettingsSection id="integrations" active={model.activeSettingsSection} title={model.t("nav.integrations")}>
    <Suspense fallback={<LoadingState scope="block" />}><IntegrationsPage embedded /></Suspense>
  </SettingsSection>;
}

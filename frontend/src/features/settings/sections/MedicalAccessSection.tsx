import { MedicalRoleWorkspace } from "../../medical/roles/MedicalRoleWorkspace";
import { SettingsSection } from "../components/SettingsLayout";
import type { SettingsModel } from "../useSettingsModel";

export function MedicalAccessSection({ model }: { model: SettingsModel }) {
  return <SettingsSection id="medical-access" active={model.activeSettingsSection} title={model.t("settings.section.medical-access")}>
    <div className="p-4 sm:p-5">{model.business ? <MedicalRoleWorkspace key={model.business.id} businessId={Number(model.business.id)}
      active={model.activeSettingsSection === "medical-access"} onDraft={model.setMedicalDraftState} /> : null}</div>
  </SettingsSection>;
}

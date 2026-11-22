import { CredentialWorkspace } from "../../medical/credentials/CredentialWorkspace";
import { SettingsSection } from "../components/SettingsLayout";
import type { SettingsModel } from "../useSettingsModel";

export function MedicalCredentialsSection({ model }: { model: SettingsModel }) {
  return <SettingsSection id="medical-credentials" active={model.activeSettingsSection} title={model.t("settings.section.medical-credentials")}>
    <div className="p-4 sm:p-5">{model.business ? <CredentialWorkspace key={model.business.id} businessId={Number(model.business.id)}
      active={model.activeSettingsSection === "medical-credentials"} onDraft={model.setCredentialDraftState} /> : null}</div>
  </SettingsSection>;
}

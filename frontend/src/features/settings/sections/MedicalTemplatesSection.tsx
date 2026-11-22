import { TemplateWorkspace } from "../../medical/templates/TemplateWorkspace";
import { SettingsSection } from "../components/SettingsLayout";
import type { SettingsModel } from "../useSettingsModel";

export function MedicalTemplatesSection({ model }: { model: SettingsModel }) {
  return <SettingsSection id="medical-templates" active={model.activeSettingsSection} title={model.t("settings.section.medical-templates")}>
    <div className="p-4 sm:p-5">{model.business ? <TemplateWorkspace key={model.business.id} businessId={Number(model.business.id)}
      active={model.activeSettingsSection === "medical-templates"} onDraft={model.setTemplateDraftState} /> : null}</div>
  </SettingsSection>;
}

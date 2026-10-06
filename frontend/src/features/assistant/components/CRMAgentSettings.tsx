import type { Dispatch, SetStateAction } from "react";
import { ToggleSwitch } from "../../../components/ui/Switch";
import { useI18n } from "../../../lib/i18n";
import type { AgentFormState } from "../aiAgentsTypes";

const sources = ["clients", "leads", "deals", "tasks", "appointments", "knowledge"];
const tools = ["crm_read", "crm_create", "crm_update", "crm_archive", "crm_restore", "crm_transition"];

export function CRMAgentSettings({ section, form, setForm, canManage }: {
  section: "sources" | "actions"; form: AgentFormState; setForm: Dispatch<SetStateAction<AgentFormState>>; canManage: boolean;
}) {
  const { t } = useI18n();
  const values = section === "sources" ? sources : tools;
  const field = section === "sources" ? "sources" : "allowed_tools";
  return <div className="mb-5 space-y-4">
    <fieldset className="grid gap-2 sm:grid-cols-2" disabled={!canManage}>
      <legend className="mb-3 text-base font-semibold">{t(section === "sources" ? "aiWorkflow.sources" : "aiWorkflow.actions")}</legend>
      {values.map(value => <label key={value} className="flex min-h-11 items-center gap-3 text-sm">
        <input type="checkbox" checked={form[field].includes(value)} onChange={event => setForm(current => ({ ...current, [field]: event.target.checked ? [...new Set([...current[field], value])] : current[field].filter(item => item !== value) }))} />
        {t(`aiWorkflow.${section === "sources" ? "source" : "tool"}.${value}`)}
      </label>)}
    </fieldset>
    {section === "actions" && <>
      <div className="flex min-h-11 items-center justify-between gap-4"><span className="text-sm">{t("aiScenario.enableAnalytics")}</span><ToggleSwitch label={t("aiScenario.enableAnalytics")} checked={form.analyst_enabled} disabled={!canManage} onChange={value => setForm(current => ({ ...current, analyst_enabled: value }))} /></div>
      <p className="text-sm text-platforma-subtle">{t("aiScenario.confirmation")}</p>
    </>}
  </div>;
}

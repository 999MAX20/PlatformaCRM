import { useState, type Dispatch, type SetStateAction } from "react";
import { Modal } from "../../../components/ui/Modal";

import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import { Textarea } from "../../../components/ui/Textarea";
import { useI18n } from "../../../lib/i18n";
import type { AgentProfile } from "../../../types";
import type { AgentFormState, BotDraftState } from "../aiAgentsTypes";
import { FieldHint } from "./AIAgentsShared";

type ProfileProps = {
  botDraft: BotDraftState;
  setBotDraft: Dispatch<SetStateAction<BotDraftState>>;
  form: AgentFormState;
  setForm: Dispatch<SetStateAction<AgentFormState>>;
  canManage: boolean;
};

export function ProfileManagerSection({ botDraft, setBotDraft, form, setForm, canManage }: ProfileProps) {
  const { t } = useI18n();
  const [templateOpen, setTemplateOpen] = useState(false);
  const applyTemplate = () => {
    setForm(current => ({ ...current, role_description: t("aiSetup.dentalRole"), system_prompt: t("aiSetup.dentalPrompt"), rules_text: t("aiAgents.defaultRules"), escalation_text: t("aiSetup.dentalEscalation") }));
    setTemplateOpen(false);
  };

  return (
    <div className="divide-y divide-platforma-border">
      <section className="pb-5">
        <h3 className="mb-3 text-base font-semibold text-platforma-ink">{t("aiAgents.generalSettings")}</h3>
        <div className="grid items-start gap-4 sm:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)]">
          <Input className="sm:min-h-10" label={t("aiAgents.name")} value={botDraft.name} disabled={!canManage} onChange={event => {
            const name = event.target.value;
            setBotDraft(current => ({ ...current, name }));
            setForm(current => ({ ...current, name }));
          }} />
          <Select className="sm:min-h-10" label={t("aiAgents.language")} value={botDraft.default_language} disabled={!canManage} onChange={event => {
            const language = event.target.value;
            setBotDraft(current => ({ ...current, default_language: language }));
            setForm(current => ({ ...current, language }));
          }} options={[
            { value: "ru", label: t("language.ru") },
            { value: "kk", label: t("language.kk") },
            { value: "en", label: t("language.en") },
          ]} />
          <Select className="sm:min-h-10" label={t("aiAgents.tone")} value={form.tone} disabled={!canManage}
            onChange={event => setForm(current => ({ ...current, tone: event.target.value as AgentProfile["tone"] }))}
            options={["friendly", "expert", "formal", "sales", "support"].map(value => ({ value, label: t(`aiAgents.tone.${value}`) }))} />
        </div>
      </section>

      <section className="py-5">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <h3 className="text-base font-semibold text-platforma-ink">{t("aiAgents.instructionTitle")}</h3>
          {botDraft.settings_json.scenario !== "crm" && <Button type="button" className="min-h-11 w-fit sm:min-h-10" variant="secondary" disabled={!canManage} onClick={() => setTemplateOpen(true)}>{t("aiWorkspace.template")}</Button>}
        </div>
        <Textarea className="h-20 !min-h-20 py-2" rows={3} label={t("aiAgents.roleDescription")} value={form.role_description} disabled={!canManage}
          onChange={event => setForm(current => ({ ...current, role_description: event.target.value }))} />
      </section>

      <section className="pt-4">
        <div id="ai-agent-quality-settings" className="space-y-3">
            <div>
              <Textarea className="min-h-20 py-2" rows={3} label={t("aiAgents.systemPrompt")} value={form.system_prompt} disabled={!canManage}
                onChange={event => setForm(current => ({ ...current, system_prompt: event.target.value }))} />
              <FieldHint>{t("aiAgents.hint.systemPrompt")}</FieldHint>
            </div>
            <div className="grid items-start gap-5 lg:grid-cols-2">
              <div>
                <Textarea className="min-h-24 py-2" rows={4} label={t("aiAgents.rules")} value={form.rules_text} disabled={!canManage}
                  onChange={event => setForm(current => ({ ...current, rules_text: event.target.value }))} />
                <FieldHint>{t("aiAgents.hint.rules")}</FieldHint>
              </div>
              <ModelsSection draft={botDraft} setDraft={setBotDraft} canManage={canManage} />
            </div>
          </div>
      </section>
      <Modal title={t("aiWorkspace.template")} open={templateOpen} onClose={() => setTemplateOpen(false)}>
        <p className="mb-4 text-sm text-platforma-subtle">{t("aiWorkspace.templateHint")}</p>
        <div className="space-y-4">
          {[["aiAgents.roleDescription", "aiSetup.dentalRole"], ["aiAgents.systemPrompt", "aiSetup.dentalPrompt"], ["aiAgents.rules", "aiAgents.defaultRules"], ["aiSetup.handoffRules", "aiSetup.dentalEscalation"]].map(([label, value]) => <div key={label}><h3 className="text-sm font-semibold">{t(label)}</h3><p className="whitespace-pre-wrap text-sm text-platforma-subtle">{t(value)}</p></div>)}
          <div className="flex flex-wrap justify-end gap-2"><Button variant="secondary" onClick={() => setTemplateOpen(false)}>{t("common.cancel")}</Button><Button disabled={!canManage} onClick={applyTemplate}>{t("aiWorkspace.fillTemplate")}</Button></div>
        </div>
      </Modal>
    </div>
  );
}

function ModelsSection({ draft, setDraft, canManage }: { draft: BotDraftState; setDraft: React.Dispatch<React.SetStateAction<BotDraftState>>; canManage: boolean }) {
  const { t } = useI18n();
  const model = String(draft.settings_json.model || "");
  const temperature = Number(draft.settings_json.temperature ?? 0.4);
  const setModel = (value: string) => setDraft((current) => ({ ...current, settings_json: { ...current.settings_json, model: value } }));
  const setTemperature = (value: number) => setDraft((current) => ({ ...current, settings_json: { ...current.settings_json, temperature: value } }));

  return (
    <section>
        <h3 className="text-base font-semibold text-midnight">{t("aiAgents.modelsTitle")}</h3>
        <div className="mt-3 grid gap-3">
          <Select
            className="sm:min-h-10"
            label={t("aiAgents.responseMode")}
            value={model}
            disabled={!canManage}
            onChange={(event) => setModel(event.target.value)}
            options={[
              { value: "", label: t("aiQuality.configuredModel") },
              ...(model && !["gpt-4.1", "gpt-4.1-mini", "gpt-4o-mini"].includes(model) ? [{ value: model, label: model }] : []),
              { value: "gpt-4.1", label: t("aiAgents.responseMode.quality") },
              { value: "gpt-4.1-mini", label: t("aiAgents.responseMode.fast") },
              { value: "gpt-4o-mini", label: t("aiAgents.responseMode.economy") },
            ]}
          />
          <FieldHint>{t("aiAgents.hint.responseMode")}</FieldHint>
          <label className="block">
            <span className="mb-2 block text-sm font-semibold text-platforma-subtle">{t("aiAgents.responseFreedom", { value: temperature.toFixed(1) })}</span>
            <input className="w-full accent-ai-600" type="range" min="0" max="1" step="0.1" value={temperature} disabled={!canManage} onChange={(event) => setTemperature(Number(event.target.value))} />
            <FieldHint>{t("aiAgents.hint.temperature")}</FieldHint>
          </label>

        </div>
      </section>
  );
}

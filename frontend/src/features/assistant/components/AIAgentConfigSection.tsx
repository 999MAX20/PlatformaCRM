import { type Dispatch, type SetStateAction } from "react";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import { Textarea } from "../../../components/ui/Textarea";
import { useI18n } from "../../../lib/i18n";
import type { AgentProfile, Bot } from "../../../types";
import type { AgentFormState, BotDraftState } from "../aiAgentsTypes";
import { FieldHint } from "./AIAgentsShared";
import { ToggleSwitch } from "../../../components/ui/Switch";
import { AgentBranchScope } from "./AgentBranchScope";

type ProfileProps = {
  botDraft: BotDraftState;
  setBotDraft: Dispatch<SetStateAction<BotDraftState>>;
  form: AgentFormState;
  setForm: Dispatch<SetStateAction<AgentFormState>>;
  canManage: boolean;
  readiness?: Bot["readiness"];
  scenario?: Bot["scenario"];
};

export function ProfileManagerSection({ botDraft, setBotDraft, form, setForm, canManage, scenario }: ProfileProps) {
  const { t } = useI18n();
  return (
    <div className="max-w-xl space-y-4">
      <section>
        <div className="grid items-start gap-3 sm:grid-cols-2">
          <div className="sm:col-span-2"><Input className="sm:min-h-9" label={t("aiAgents.name")} value={botDraft.name} disabled={!canManage} onChange={event => {
            const name = event.target.value;
            setBotDraft(current => ({ ...current, name }));
            setForm(current => ({ ...current, name }));
          }} /></div>
          <Select density="compact" className="min-h-11 sm:min-h-9 sm:py-1" label={t("aiAgents.language")} value={botDraft.default_language} disabled={!canManage} onChange={event => {
            const language = event.target.value;
            setBotDraft(current => ({ ...current, default_language: language }));
            setForm(current => ({ ...current, language }));
          }} options={[
            { value: "ru", label: t("language.ru") },
            { value: "kk", label: t("language.kk") },
            { value: "en", label: t("language.en") },
          ]} />
          <Select density="compact" className="min-h-11 sm:min-h-9 sm:py-1" label={t("aiAgents.tone")} value={form.tone} disabled={!canManage}
            onChange={event => setForm(current => ({ ...current, tone: event.target.value as AgentProfile["tone"] }))}
            options={["friendly", "expert", "formal", "sales", "support"].map(value => ({ value, label: t(`aiAgents.tone.${value}`) }))} />
        </div>
      </section>
      {scenario !== "crm" && <AgentBranchScope draft={botDraft} setDraft={setBotDraft} disabled={!canManage} />}
    </div>
  );
}

export function InstructionsSection({ form, setForm, canManage }: ProfileProps) {
  const { t } = useI18n();
  return (
    <div className="max-w-2xl space-y-4">
      <section>
        <Textarea className="!min-h-16 py-2" rows={2} label={t("aiAgents.roleDescription")} value={form.role_description} disabled={!canManage}
          onChange={event => setForm(current => ({ ...current, role_description: event.target.value }))} />
      </section>

      <section>
        <div id="ai-agent-quality-settings" className="space-y-3">
            <div>
              <Textarea className="min-h-40 py-2" rows={6} label={t("aiAgents.systemPrompt")} value={form.system_prompt} disabled={!canManage}
                onChange={event => setForm(current => ({ ...current, system_prompt: event.target.value }))} />
              <FieldHint>{t("aiAgents.hint.systemPrompt")}</FieldHint>
            </div>
              <div>
                <Textarea className="!min-h-20 py-2" rows={3} label={t("aiAgents.rules")} value={form.rules_text} disabled={!canManage}
                  onChange={event => setForm(current => ({ ...current, rules_text: event.target.value }))} />
                <FieldHint>{t("aiAgents.hint.rules")}</FieldHint>
              </div>
          </div>
      </section>
    </div>
  );
}

export function ModelsSection({ draft, setDraft, canManage, readiness }: { draft: BotDraftState; setDraft: React.Dispatch<React.SetStateAction<BotDraftState>>; canManage: boolean; readiness?: Bot["readiness"] }) {
  const { t } = useI18n();
  const model = String(draft.settings_json.model || "");
  const temperature = Number(draft.settings_json.temperature ?? 0.4);
  const configuredOptions = readiness?.provider?.model_options || [];
  const tierLabels = { smart: "quality", fast: "fast", cheap: "economy" };
  const setModel = (value: string) => setDraft((current) => ({ ...current, settings_json: { ...current.settings_json, model: value } }));
  const setTemperature = (value: number) => setDraft((current) => ({ ...current, settings_json: { ...current.settings_json, temperature: value } }));

  return (
    <section className="max-w-xl">
        <div className="grid gap-3">
          <Select
            density="compact" className="min-h-11 sm:min-h-9 sm:py-1"
            label={t("aiAgents.responseMode")}
            value={model}
            disabled={!canManage}
            onChange={(event) => setModel(event.target.value)}
            options={[
              { value: "", label: t("aiQuality.configuredModel") },
              ...(model && !configuredOptions.some(option => option.value === model) ? [{ value: model, label: model }] : []),
              ...configuredOptions.map(option => ({ value: option.value, label: t(`aiAgents.responseMode.${tierLabels[option.tier]}`) })),
            ]}
          />
          <FieldHint>{t("aiAgents.hint.responseMode")}</FieldHint>
          <FieldHint>{t("aiAgents.readiness.modelOptions")}</FieldHint>
          <label className="block">
            <span className="mb-2 block text-sm font-semibold text-platforma-subtle">{t("aiAgents.responseFreedom", { value: temperature.toFixed(1) })}</span>
            <input className="w-full accent-ai-600" type="range" min="0" max="1" step="0.1" value={temperature} disabled={!canManage} onChange={(event) => setTemperature(Number(event.target.value))} />
            <FieldHint>{t("aiAgents.hint.temperature")}</FieldHint>
          </label>
          <div className="flex items-center justify-between gap-4">
            <span className="text-sm font-semibold text-platforma-subtle">{t("agentChat.memorySetting")}</span>
            <ToggleSwitch label={t("agentChat.memorySetting")} checked={draft.settings_json.memory_enabled !== false} disabled={!canManage}
              onChange={value => setDraft(current => ({ ...current, settings_json: { ...current.settings_json, memory_enabled: value } }))} />
          </div>
          <FieldHint>{t("agentChat.memoryHint")}</FieldHint>

        </div>
      </section>
  );
}

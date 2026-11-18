import { useId, type Dispatch, type SetStateAction } from "react";
import { Link } from "react-router";
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
          <div>
          <Select density="compact" className="min-h-11 sm:min-h-9 sm:py-1" label={t(scenario === "crm" ? "aiAgents.language" : "aiAgents.fallbackLanguage")} value={botDraft.default_language} disabled={!canManage} onChange={event => {
            const language = event.target.value;
            setBotDraft(current => ({ ...current, default_language: language }));
            setForm(current => ({ ...current, language }));
          }} options={[
            { value: "ru", label: t("language.ru") },
            { value: "kk", label: t("language.kk") },
            { value: "en", label: t("language.en") },
          ]} />
          {scenario !== "crm" && <FieldHint>{t("aiAgents.customerLanguageHint")}</FieldHint>}
          </div>
          <Select density="compact" className="min-h-11 sm:min-h-9 sm:py-1" label={t("aiAgents.tone")} value={form.tone} disabled={!canManage}
            onChange={event => setForm(current => ({ ...current, tone: event.target.value as AgentProfile["tone"] }))}
            options={["friendly", "expert", "formal", "sales", "support"].map(value => ({ value, label: t(`aiAgents.tone.${value}`) }))} />
        </div>
      </section>
      {scenario !== "crm" && <AgentBranchScope draft={botDraft} setDraft={setBotDraft} disabled={!canManage} />}
    </div>
  );
}

export function InstructionsSection({ form, setForm, canManage, botId, scenario }: ProfileProps & { botId: Bot["id"] }) {
  const { t } = useI18n();
  const id = useId();
  const rowClass = "grid max-w-2xl items-start gap-x-6 gap-y-2 @min-[60rem]:max-w-none @min-[60rem]:grid-cols-[minmax(0,42rem)_minmax(16rem,18rem)]";
  const hintClass = "min-w-0 space-y-2 text-sm leading-5 text-platforma-subtle @min-[60rem]:pt-7";
  return (
    <div className="@container max-w-[62rem] space-y-4">
      <section className={rowClass}>
        <Textarea className="!min-h-16 py-2" rows={2} label={t("aiAgents.roleDescription")} value={form.role_description} disabled={!canManage}
          aria-describedby={`${id}-role-hint`}
          onChange={event => setForm(current => ({ ...current, role_description: event.target.value }))} />
        <div id={`${id}-role-hint`} className={hintClass}>
          <p className="font-semibold">{t("aiAgents.hint.role")}</p>
          <p>{t("aiAgents.hint.roleExample")}</p>
        </div>
      </section>

      <section>
        <div id="ai-agent-quality-settings" className="space-y-3">
          <div className={rowClass}>
              <Textarea id={`${id}-instruction`} label={t("aiAgents.systemPrompt")} className="min-h-40 py-2" rows={6}
                aria-describedby={`${id}-instruction-hint ${id}-actions-hint`} value={form.system_prompt} disabled={!canManage}
                onChange={event => setForm(current => ({ ...current, system_prompt: event.target.value }))} />
            <div className={hintClass}>
              <p id={`${id}-instruction-hint`}>{t("aiAgents.hint.systemPrompt")}</p>
              <p id={`${id}-actions-hint`}>{t(scenario === "crm" ? "aiAgents.instructions.actionsHintCrm" : "aiAgents.instructions.actionsHint")}</p>
              <Link to={`/app/ai-agents/${botId}/actions`} className="platforma-focus-ring inline-flex min-h-11 items-center rounded-control text-sm font-semibold text-brand-800 underline hover:text-brand-900">
                {t("aiAgents.instructions.openActions")}
              </Link>
            </div>
          </div>
          <div className={rowClass}>
            <Textarea className="!min-h-20 py-2" rows={3} label={t("aiAgents.rules")} value={form.rules_text} disabled={!canManage}
              aria-describedby={`${id}-rules-hint`}
              onChange={event => setForm(current => ({ ...current, rules_text: event.target.value }))} />
            <div id={`${id}-rules-hint`} className={hintClass}>
              <p className="font-semibold">{t("aiAgents.hint.rules")}</p>
              <p>{t("aiAgents.hint.rulesExample")}</p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

export function ModelsSection({ draft, setDraft, canManage, readiness, scenario }: { draft: BotDraftState; setDraft: React.Dispatch<React.SetStateAction<BotDraftState>>; canManage: boolean; readiness?: Bot["readiness"]; scenario?: Bot["scenario"] }) {
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
          {scenario === "inbox" && <>
            <Select density="compact" label={t("aiSetup.batch.label")}
              value={String(draft.settings_json.inbound_wait_seconds || 0)} disabled={!canManage}
              onChange={event => setDraft(current => ({ ...current, settings_json: { ...current.settings_json, inbound_wait_seconds: Number(event.target.value) } }))}
              options={[{ value: "0", label: t("aiSetup.batch.off") }, ...[2, 3, 5].map(seconds => ({ value: String(seconds), label: t("aiSetup.batch.seconds", { seconds }) }))]} />
            <FieldHint>{t("aiSetup.batch.hint")}</FieldHint>
          </>}

        </div>
      </section>
  );
}

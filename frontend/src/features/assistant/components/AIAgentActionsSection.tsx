import { Input } from "../../../components/ui/Input";
import { Textarea } from "../../../components/ui/Textarea";
import { Select } from "../../../components/ui/Select";
import { Button } from "../../../components/ui/Button";
import { ToggleSwitch } from "../../../components/ui/Switch";
import { useI18n } from "../../../lib/i18n";
import type { BotChannel } from "../../../types";
import type { AgentFormState, BotDraftState } from "../aiAgentsTypes";
import { customerActionsFromSettings, customerActionsSettings, type CreationPolicy } from "../customerActions";
import { CustomerSafetySettings } from "./CustomerSafetySettings";

export function AgentActionsSection({ botDraft, setBotDraft, form, setForm, canManage, channels = [] }: {
  botDraft: BotDraftState;
  setBotDraft: React.Dispatch<React.SetStateAction<BotDraftState>>;
  form: AgentFormState;
  setForm: React.Dispatch<React.SetStateAction<AgentFormState>>;
  canManage: boolean;
  channels?: BotChannel[];
}) {
  const { t } = useI18n();
  const config = customerActionsFromSettings(botDraft.settings_json);
  const raw = botDraft.settings_json.auto_crm_pipeline as Record<string, unknown> | undefined;
  const legacy = raw?.mode !== "customer_actions" && (Boolean(raw && Object.keys(raw).length)
    || channels.some(channel => Boolean(channel.config_json?.auto_crm_pipeline)));
  const update = (patch: Partial<typeof config>, tool?: string, enabled?: boolean) => {
    setBotDraft(current => ({ ...current, settings_json: customerActionsSettings(current.settings_json, patch) }));
    setForm(current => {
      const tools = current.allowed_tools.filter(item => item !== "create_lead" && item !== "create_deal" && item !== tool);
      if (tool && enabled) tools.push(tool);
      return { ...current, allowed_tools: tools };
    });
  };
  const options = [
    { value: "off", label: t("aiAgents.authority.off") },
    { value: "staff_confirmation", label: t("aiAgents.authority.staffConfirmation") },
    { value: "automatic", label: t("aiAgents.authority.automatic") },
  ];
  return <div className="max-w-2xl space-y-5">
    {legacy && <div className="space-y-2 rounded-lg border border-platforma-border p-3">
      <p className="text-sm text-platforma-subtle">{t("aiAgents.actions.legacyHint")}</p>
      <Button variant="secondary" disabled={!canManage} onClick={() => update({})}>{t("aiAgents.actions.update")}</Button>
    </div>}
    <section className="space-y-4 border-b border-platforma-border pb-5">
      <ActionToggle title={t("aiAgents.actions.processing")} hint={t("aiAgents.actions.processingHint")}
        checked={config.enabled} disabled={!canManage} onChange={enabled => update({ enabled })} />
      <ActionToggle title={t("aiAgents.control.autoReplyTitle")} hint={t("aiAgents.control.autoReplyText")}
        checked={config.auto_send_reply} disabled={!canManage || !config.enabled}
        onChange={auto_send_reply => update({ auto_send_reply })} />
    </section>
    <section className="space-y-4 border-b border-platforma-border pb-5">
      <ActionToggle title={t("aiAgents.functions.clientTitle")} hint={t("aiAgents.actions.clientHint")}
        checked={form.allowed_tools.includes("create_client")} disabled={!canManage || !config.enabled}
        onChange={enabled => update({}, "create_client", enabled)} />
      <div className="grid gap-4 sm:grid-cols-2">
        {(["task", "appointment"] as const).map(action => {
          const tool = `create_${action}`;
          const field = `${action}_creation_policy` as const;
          const enabled = form.allowed_tools.includes(tool) && (action !== "appointment" || config.create_appointment);
          return <div key={action}>
            <Select density="compact" className="min-h-11 sm:min-h-9 sm:py-1 [&>span]:whitespace-normal [&>span]:text-clip"
              label={t(`aiAgents.actions.${action}`)} value={enabled ? config[field] : "off"}
              disabled={!canManage || !config.enabled} options={options}
              onChange={event => {
                const value = event.target.value;
                update({ [field]: value === "off" ? "staff_confirmation" : value as CreationPolicy,
                  ...(action === "appointment" ? { create_appointment: value !== "off" } : {}),
                }, tool, value !== "off");
              }} />
            <p className="mt-1 text-sm text-platforma-subtle">{t(`aiAgents.actions.${action}Hint`)}</p>
          </div>;
        })}
      </div>
    </section>
    <CustomerSafetySettings botDraft={botDraft} setBotDraft={setBotDraft} canManage={canManage}>
      <Input className="sm:min-h-9" type="number" min={120} max={2000} step={1}
        label={t("aiAgents.control.maxReplyChars")} value={config.max_auto_reply_chars} disabled={!canManage}
        onChange={event => update({ max_auto_reply_chars: Number(event.target.value) })} />
    </CustomerSafetySettings>
    <Textarea className="min-h-20 py-2" rows={2} label={t("aiSetup.handoffRules")} value={form.escalation_text}
      disabled={!canManage} onChange={event => setForm(current => ({ ...current, escalation_text: event.target.value }))} />
  </div>;
}

function ActionToggle({ title, hint, checked, disabled, onChange }: {
  title: string; hint: string; checked: boolean; disabled: boolean; onChange: (value: boolean) => void;
}) {
  return <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-4">
    <div className="py-2 text-sm"><h3 className="font-semibold text-midnight">{title}</h3>
      <p className="mt-1 text-platforma-subtle">{hint}</p></div>
    <div className="flex min-h-11 items-center"><ToggleSwitch label={title} checked={checked} disabled={disabled} onChange={onChange} /></div>
  </div>;
}

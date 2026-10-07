import type { Dispatch, SetStateAction } from "react";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import { ToggleSwitch } from "../../../components/ui/Switch";
import { useI18n } from "../../../lib/i18n";
import type { BotDraftState } from "../aiAgentsTypes";

const defaults = {
  allow_first_off_topic: true, off_topic_handoff_after: 3, calls_per_24h: 30,
  messages_per_minute: 12, max_message_chars: 4000, repeat_handoff_after: 3,
};
type SafetySettings = typeof defaults;

function readSettings(settings: Record<string, unknown>): SafetySettings {
  const source = settings.customer_safety;
  const value = source && typeof source === "object" && !Array.isArray(source) ? source as Record<string, unknown> : {};
  return {
    allow_first_off_topic: typeof value.allow_first_off_topic === "boolean" ? value.allow_first_off_topic : true,
    off_topic_handoff_after: typeof value.off_topic_handoff_after === "number" ? value.off_topic_handoff_after : 3,
    calls_per_24h: typeof value.calls_per_24h === "number" ? value.calls_per_24h : 30,
    messages_per_minute: typeof value.messages_per_minute === "number" ? value.messages_per_minute : 12,
    max_message_chars: typeof value.max_message_chars === "number" ? value.max_message_chars : 4000,
    repeat_handoff_after: typeof value.repeat_handoff_after === "number" ? value.repeat_handoff_after : 3,
  };
}

export function CustomerSafetySettings({ botDraft, setBotDraft, canManage }: {
  botDraft: BotDraftState; setBotDraft: Dispatch<SetStateAction<BotDraftState>>; canManage: boolean;
}) {
  const { t } = useI18n();
  const config = readSettings(botDraft.settings_json);
  const change = (patch: Partial<SafetySettings>) => setBotDraft(current => ({
    ...current, settings_json: { ...current.settings_json, customer_safety: { ...readSettings(current.settings_json), ...patch } },
  }));
  return <section aria-labelledby="customer-safety-title" className="space-y-4 border-b border-platforma-border pb-5">
    <h3 id="customer-safety-title" className="text-base font-semibold text-midnight">{t("customerSafety.title")}</h3>
    <div className="flex items-center justify-between gap-4">
      <span className="text-sm">{t("customerSafety.firstReply")}</span>
      <ToggleSwitch label={t("customerSafety.firstReply")} checked={config.allow_first_off_topic} disabled={!canManage}
        onChange={value => change({ allow_first_off_topic: value })} />
    </div>
    <Select label={t("customerSafety.offTopicLimit")} value={String(config.off_topic_handoff_after)} disabled={!canManage}
      onChange={event => change({ off_topic_handoff_after: Number(event.target.value) })}
      options={[1, 2, 3].map(value => ({ value: String(value), label: t(`customerSafety.offTopic${value}`) }))} />
    <p className="text-sm text-platforma-subtle">{t("customerSafety.offTopicHint")}</p>
    <div className="grid gap-4 sm:grid-cols-2">
      <Input type="number" min={1} max={30} step={1} label={t("customerSafety.callLimit")} disabled={!canManage}
        value={config.calls_per_24h} onChange={event => change({ calls_per_24h: Number(event.target.value) })} />
      <Input type="number" min={3} max={30} step={1} label={t("customerSafety.messageRate")} disabled={!canManage}
        value={config.messages_per_minute} onChange={event => change({ messages_per_minute: Number(event.target.value) })} />
      <Input type="number" min={2} max={10} step={1} label={t("customerSafety.repeatLimit")} disabled={!canManage}
        value={config.repeat_handoff_after} onChange={event => change({ repeat_handoff_after: Number(event.target.value) })} />
      <Input type="number" min={256} max={8000} step={1} label={t("customerSafety.messageLength")} disabled={!canManage}
        value={config.max_message_chars} onChange={event => change({ max_message_chars: Number(event.target.value) })} />
    </div>
    <p className="text-sm text-platforma-subtle">{t("customerSafety.budgetHint")}</p>
    <p className="text-sm text-platforma-subtle">{t("customerSafety.requiredPolicy")}</p>
  </section>;
}

import { useState } from "react";
import { ChevronRight } from "lucide-react";

import { Input } from "../../../components/ui/Input";
import { Textarea } from "../../../components/ui/Textarea";
import { Select } from "../../../components/ui/Select";
import { ToggleSwitch } from "../../../components/ui/Switch";
import { useI18n } from "../../../lib/i18n";
import { cn } from "../../../lib/cn";
import type { AgentFormState, AutoPipelineMode, BotDraftState } from "../aiAgentsTypes";
import { autoPipelineFromSettings } from "../aiAgentsUtils";
import { FieldHint } from "./AIAgentsShared";
import { CustomerSafetySettings } from "./CustomerSafetySettings";
export function AgentActionsSection({
  botDraft,
  setBotDraft,
  form,
  setForm,
  canManage,
}: {
  botDraft: BotDraftState;
  setBotDraft: React.Dispatch<React.SetStateAction<BotDraftState>>;
  form: AgentFormState;
  setForm: React.Dispatch<React.SetStateAction<AgentFormState>>;
  canManage: boolean;
}) {
  const { t } = useI18n();
  const runtime = autoPipelineFromSettings(botDraft.settings_json || {});
  const toolEnabled = (tool: string) => form.allowed_tools.includes(tool);
  const proposesWork = runtime.enabled && (runtime.mode === "lead_task" || runtime.mode === "draft_deal");
  return (
    <div className="space-y-5">
      <ControlSection botDraft={botDraft} setBotDraft={setBotDraft} canManage={canManage} />
      <FunctionsSection form={form} setForm={setForm} canManage={canManage} />
      <CustomerSafetySettings botDraft={botDraft} setBotDraft={setBotDraft} canManage={canManage} />
      <section className="border-b border-platforma-border pb-5 last:border-0">
        <div>
          <h3 className="text-base font-semibold text-midnight">{t("aiAgents.authority.title")}</h3>
          <p className="mt-1 text-sm font-semibold text-platforma-faint">{t("aiAgents.authority.text")}</p>
          <div className="mt-3 grid grid-cols-2 gap-3 lg:grid-cols-4 lg:divide-x lg:divide-platforma-border">
            <AuthorityRow label={t("aiAgents.authority.suggestions")} value={t(runtime.enabled && runtime.auto_send_reply ? "aiAgents.authority.autoReply" : "aiAgents.authority.suggestOnly")} />
            <AuthorityRow
              label={t("aiAgents.authority.leadTask")}
              value={proposesWork && (toolEnabled("create_lead") || toolEnabled("create_task")) ? t(runtime.creation_policy === "automatic" ? "aiAgents.authority.automatic" : "aiAgents.authority.staffConfirmation") : t("aiAgents.authority.off")}
            />
            <AuthorityRow
              label={t("aiAgents.authority.draftDeal")}
              value={runtime.enabled && runtime.mode === "draft_deal" && toolEnabled("create_deal") ? t(runtime.creation_policy === "automatic" ? "aiAgents.authority.automatic" : "aiAgents.authority.staffConfirmation") : t("aiAgents.authority.off")}
            />
            <AuthorityRow
              label={t("aiAgents.authority.appointment")}
              value={runtime.creation_policy === "automatic" && runtime.enabled && runtime.create_appointment && toolEnabled("create_appointment") ? t("aiAgents.authority.customerSelection") : t("aiAgents.authority.staffBooking")}
            />
          </div>
        </div>
      </section>
      <section className="border-b border-platforma-border pb-5 last:border-0"><div>
        <Textarea className="min-h-20 py-2" rows={2} label={t("aiSetup.handoffRules")} value={form.escalation_text} disabled={!canManage} onChange={(event) => setForm((current) => ({ ...current, escalation_text: event.target.value }))} />
      </div></section>
    </div>
  );
}

function AuthorityRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1 text-sm lg:px-3 lg:first:pl-0">
      <span className="font-semibold text-platforma-subtle">{label}</span>
      <span className="font-semibold text-midnight">{value}</span>
    </div>
  );
}

function ControlSection({ botDraft, setBotDraft, canManage }: { botDraft: BotDraftState; setBotDraft: React.Dispatch<React.SetStateAction<BotDraftState>>; canManage: boolean }) {
  const { t } = useI18n();
  const config = autoPipelineFromSettings(botDraft.settings_json);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const setConfig = (update: (current: typeof config) => typeof config) => setBotDraft((current) => ({
    ...current, settings_json: { ...current.settings_json, auto_crm_pipeline: update(autoPipelineFromSettings(current.settings_json)) },
  }));

  return (
    <section className="border-b border-platforma-border pb-5 last:border-0">
      <div>
        <div className="mb-3">
          <h3 className="text-base font-semibold text-midnight">{t("aiAgents.control.pipelineTitle")}</h3>
          <p className="mt-1 text-sm font-semibold text-platforma-faint">{t("aiAgents.control.pipelineText")}</p>
        </div>

        <div className="grid items-end gap-x-5 gap-y-1 lg:grid-cols-[minmax(240px,480px)_minmax(0,1fr)]">
        <Select
          className="sm:min-h-10"
          label={t("aiAgents.control.mode")}
          value={config.mode}
          disabled={!canManage}
          onChange={(event) => {
            const mode = event.target.value as AutoPipelineMode;
            setConfig((current) => ({ ...current, mode, enabled: mode !== "off" }));
          }}
          options={[
            { value: "off", label: t("aiAgents.control.mode.off") },
            { value: "triage", label: t("aiAgents.control.mode.triage") },
            { value: "lead_task", label: t("aiAgents.control.mode.leadTask") },
            { value: "draft_deal", label: t("aiAgents.control.mode.draftDeal") },
          ]}
        />
        <FieldHint>{t("aiAgents.hint.pipelineMode")}</FieldHint>
        </div>

        <div className="mt-3 max-w-xl">
          <Select label={t("aiAgents.creationPolicy")} value={config.creation_policy} disabled={!canManage}
            onChange={event => setConfig(current => ({ ...current, creation_policy: event.target.value }))}
            options={[
              { value: "staff_confirmation", label: t("aiAgents.authority.staffConfirmation") },
              { value: "automatic", label: t("aiAgents.authority.automatic") },
            ]} />
          <FieldHint>{t("aiAgents.creationPolicyHint")}</FieldHint>
        </div>

        <div className="mt-3 divide-y divide-platforma-border">
          {[
            ["require_review_on_fallback", t("aiAgents.control.reviewFallbackTitle"), t("aiAgents.control.reviewFallbackText")],
            ["create_appointment", t("aiAgents.control.appointmentTitle"), t("aiAgents.control.appointmentText")],
            ["auto_send_reply", t("aiAgents.control.autoReplyTitle"), t("aiAgents.control.autoReplyText")],
          ].map(([key, title, text]) => (
            <div key={key} className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-4 py-1">
              <div className="py-2 text-sm">
                <h4 className="mb-1 font-semibold text-midnight">{title}</h4>
                <p className="pb-2 leading-5 text-platforma-subtle">{text}</p>
              </div>
              <div className="flex min-h-11 items-center sm:min-h-9">
                <ToggleSwitch
                  checked={Boolean(config[key as keyof typeof config])}
                  disabled={!canManage || config.mode === "off"}
                  label={title}
                  tone="ai"
                  onChange={(next) => setConfig((current) => ({ ...current, [key]: next }))}
                />
              </div>
            </div>
          ))}
        </div>

        <div className="mt-2">
          <button
            type="button"
            className="platforma-focus-ring flex min-h-11 w-full items-center justify-between gap-3 text-left"
            onClick={() => setShowAdvanced((value) => !value)}
            aria-expanded={showAdvanced}
            aria-controls="ai-agent-pipeline-advanced"
          >
            <h4 className="font-semibold text-midnight">{t("aiAgents.control.advancedTitle")}</h4>
            <ChevronRight size={18} className={cn("shrink-0 text-platforma-faint transition", showAdvanced && "rotate-90 text-ai-700")} />
          </button>

          {showAdvanced ? (
            <div id="ai-agent-pipeline-advanced" className="mt-3 grid gap-3 md:grid-cols-2">
              <p className="text-sm leading-5 text-platforma-subtle md:col-span-2">{t("aiAgents.control.advancedText")}</p>
              <div>
                <Input
                  label={t("aiAgents.control.maxReplyChars")}
                  type="number"
                  min={120}
                  max={2000}
                  value={config.max_auto_reply_chars}
                  disabled={!canManage}
                  onChange={(event) => setConfig((current) => ({ ...current, max_auto_reply_chars: Math.max(120, Math.min(Number(event.target.value) || 900, 2000)) }))}
                />
                <FieldHint>{t("aiAgents.hint.maxReplyChars")}</FieldHint>
              </div>
              <label className="block">
                <span className="mb-2 block text-sm font-semibold text-platforma-subtle">{t("aiAgents.control.leadConfidence", { value: config.min_lead_confidence.toFixed(1) })}</span>
                <input className="w-full accent-ai-600" type="range" min="0.1" max="1" step="0.1" value={config.min_lead_confidence} disabled={!canManage} onChange={(event) => setConfig((current) => ({ ...current, min_lead_confidence: Number(event.target.value) }))} />
                <FieldHint>{t("aiAgents.hint.leadConfidence")}</FieldHint>
              </label>
              <label className="block md:col-span-2">
                <span className="mb-2 block text-sm font-semibold text-platforma-subtle">{t("aiAgents.control.dealConfidence", { value: config.min_deal_confidence.toFixed(1) })}</span>
                <input className="w-full accent-ai-600" type="range" min="0.1" max="1" step="0.1" value={config.min_deal_confidence} disabled={!canManage} onChange={(event) => setConfig((current) => ({ ...current, min_deal_confidence: Number(event.target.value) }))} />
                <FieldHint>{t("aiAgents.hint.dealConfidence")}</FieldHint>
              </label>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}

function FunctionsSection({
  form,
  setForm,
  canManage,
}: {
  form: AgentFormState;
  setForm: React.Dispatch<React.SetStateAction<AgentFormState>>;
  canManage: boolean;
}) {
  const { t } = useI18n();
  const tools = [
    ["create_client", t("aiAgents.functions.clientTitle"), t("aiAgents.functions.clientText")],
    ["create_appointment", t("aiAgents.functions.bookingTitle"), t("aiAgents.functions.bookingText")],
    ["create_lead", t("aiAgents.functions.leadTitle"), t("aiAgents.functions.leadText")],
    ["create_task", t("aiAgents.functions.taskTitle"), t("aiAgents.functions.taskText")],
    ["create_deal", t("aiAgents.functions.dealTitle"), t("aiAgents.functions.dealText")],
    ["handoff_to_manager", t("aiAgents.functions.managerTitle"), t("aiAgents.functions.managerText")],
  ];
  const toggleTool = (tool: string, enabled: boolean) => {
    setForm((current) => ({
      ...current,
      allowed_tools: enabled
        ? Array.from(new Set([...current.allowed_tools, tool]))
        : current.allowed_tools.filter((item) => item !== tool),
    }));
  };

  return (
    <section className="border-b border-platforma-border pb-5 last:border-0">
      <div>
        <h3 className="mb-3 text-base font-semibold text-platforma-ink">{t("aiAgents.functionsTitle")}</h3>
        <div className="divide-y divide-platforma-border">
        {tools.map(([key, title, text]) => {
          const enabled = key === "handoff_to_manager" || form.allowed_tools.includes(key);
          return (
            <div key={key} className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-4 py-1">
              <div className="min-w-0 py-2 text-sm">
                <h4 className="mb-1 font-semibold text-platforma-ink">{title}</h4>
                <div className="pb-2">
                  <p className="leading-5 text-platforma-subtle">{text}</p>
                  <FieldHint>{t(`aiAgents.hint.tool.${key}`)}</FieldHint>
                </div>
              </div>
              <div className="flex min-h-11 shrink-0 items-center gap-2 sm:min-h-9">
                <span className="text-xs font-semibold text-platforma-subtle">{enabled ? t("aiAgents.functions.enabled") : t("aiAgents.functions.disabled")}</span>
                <ToggleSwitch checked={enabled} disabled={!canManage || key === "handoff_to_manager"} label={title} tone="ai" onChange={(next) => toggleTool(key, next)} />
              </div>
            </div>
          );
        })}
        </div>
      </div>
    </section>
  );
}

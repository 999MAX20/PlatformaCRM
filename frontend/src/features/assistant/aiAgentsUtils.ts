import { BookOpen, Bot, FunctionSquare, MessageSquareText, Radio, Settings } from "lucide-react";

import type { AgentProfile, Bot as BotType, BotChannel, Id } from "../../types";
import type { AgentFormState, AgentSection, AutoPipelineMode, OnboardingStep } from "./aiAgentsTypes";

export const defaultAllowedTools = ["create_client", "create_appointment", "handoff_to_manager"];

export const sections: Array<{ id: AgentSection; labelKey: string; titleKey: string; icon: typeof Settings }> = [
  { id: "overview", labelKey: "aiAgents.section.overview", titleKey: "aiAgents.section.overview", icon: MessageSquareText },
  { id: "profile", labelKey: "aiAgents.section.profile", titleKey: "aiAgents.profileTitle", icon: Bot },
  { id: "instructions", labelKey: "aiAgents.section.instructions", titleKey: "aiAgents.section.instructions", icon: BookOpen },
  { id: "knowledge", labelKey: "aiAgents.section.knowledgeSimple", titleKey: "aiAgents.knowledgeTitle", icon: BookOpen },
  { id: "actions", labelKey: "aiAgents.section.actions", titleKey: "aiAgents.actionsTitle", icon: FunctionSquare },
  { id: "channels", labelKey: "aiAgents.section.channels", titleKey: "aiAgents.channelsTitle", icon: Radio },
  { id: "advanced", labelKey: "aiAgents.section.advanced", titleKey: "aiAgents.section.advanced", icon: Settings },
];

const legacySectionMap: Record<string, AgentSection> = {
  test: "test",
  settings: "profile",
  prompting: "instructions",
  models: "advanced",
  integrations: "knowledge",
  control: "actions",
  functions: "actions",
  messages: "test",
};

export function jsonFromLines(text: string) {
  return {
    items: text
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean),
  };
}

export function formFromProfile(profile: AgentProfile): AgentFormState {
  const tools = Array.isArray(profile.allowed_tools_json?.tools)
    ? (profile.allowed_tools_json.tools as unknown[]).map(String)
    : defaultAllowedTools;
  return {
    id: profile.id,
    name: profile.name,
    bot: profile.bot ? String(profile.bot) : "",
    role_description: profile.role_description,
    tone: profile.tone,
    language: profile.language,
    is_active: profile.is_active,
    system_prompt: profile.system_prompt,
    sources: Array.isArray(profile.rules_json?.sources) ? profile.rules_json.sources as string[] : ["clients", "leads", "deals", "tasks", "appointments", "knowledge"],
    analyst_enabled: profile.rules_json?.analyst_enabled !== false,
    rules_text: Array.isArray(profile.rules_json?.items) ? (profile.rules_json.items as string[]).join("\n") : "",
    escalation_text: Array.isArray(profile.escalation_rules_json?.items) ? (profile.escalation_rules_json.items as string[]).join("\n") : "",
    allowed_tools: tools,
  };
}

export function createDefaultProfile(bot: BotType | null | undefined, t: (key: string) => string): AgentFormState {
  const crm = bot?.scenario === "crm";
  return {
    id: null,
    name: bot?.name || t("aiAgents.defaultName"),
    bot: bot ? String(bot.id) : "",
    role_description: crm ? "" : t("aiSetup.dentalRole"),
    tone: crm ? "expert" : "friendly",
    language: bot?.default_language || "ru",
    is_active: true,
    system_prompt: crm ? "" : t("aiSetup.dentalPrompt"),
    sources: ["clients", "leads", "deals", "tasks", "appointments", "knowledge"],
    analyst_enabled: true,
    rules_text: crm ? "" : t("aiAgents.defaultRules"),
    escalation_text: crm ? "" : t("aiSetup.dentalEscalation"),
    allowed_tools: crm ? ["crm_read"] : defaultAllowedTools,
  };
}

export function autoPipelineFromSettings(settings: Record<string, unknown>) {
  const raw = settings.auto_crm_pipeline && typeof settings.auto_crm_pipeline === "object"
    ? settings.auto_crm_pipeline as Record<string, unknown>
    : {};
  const legacyModes: Record<string, AutoPipelineMode> = { suggest_only: "triage", auto_lead_task: "lead_task", draft_deal: "draft_deal", appointment_explicit: "lead_task" };
  const legacyMode = typeof raw.confirmation_mode === "string" ? legacyModes[raw.confirmation_mode] : undefined;
  const mode = typeof raw.mode === "string" && ["off", "triage", "lead_task", "draft_deal", "customer_actions"].includes(raw.mode)
    ? raw.mode as AutoPipelineMode
    : legacyMode || "off";
  return {
    enabled: Boolean(raw.enabled ?? mode !== "off"),
    creation_policy: raw.creation_policy === "automatic" ? "automatic" : "staff_confirmation",
    mode,
    min_lead_confidence: Number(raw.min_lead_confidence ?? 0.7),
    min_deal_confidence: Number(raw.min_deal_confidence ?? 0.8),
    require_review_on_fallback: raw.require_review_on_fallback !== false,
    create_appointment: Boolean(raw.create_appointment),
    auto_send_reply: Boolean(raw.auto_send_reply),
    max_auto_reply_chars: Number(raw.max_auto_reply_chars ?? 900),
  };
}

export function canonicalSection(value?: string): AgentSection {
  if (!value) return "profile";
  if (sections.some((item) => item.id === value)) return value as AgentSection;
  return legacySectionMap[value] || "profile";
}

export function channelStatus(channel: BotChannel | undefined, t: (key: string) => string) {
  if (!channel) return t("aiAgents.status.notConnected");
  if (channel.status === "active") return t("aiAgents.status.connected");
  if (channel.status === "error") return t("aiAgents.status.error");
  if (channel.status === "paused") return t("aiAgents.channel.paused");
  return t("aiAgents.status.setup");
}

export function channelStatusClass(channel?: BotChannel) {
  if (!channel || channel.status === "paused") return "bg-surface-muted text-platforma-subtle ring-platforma-border";
  if (channel.status === "active") return "bg-[var(--platforma-success-soft)] text-platforma-success ring-platforma-success/20";
  if (channel.status === "error") return "bg-[var(--platforma-danger-soft)] text-platforma-danger ring-platforma-danger/20";
  return "bg-[var(--platforma-warning-soft)] text-platforma-warning ring-platforma-warning/20";
}

export function agentStatusLabel(bot: BotType, t: (key: string) => string) {
  if (bot.status === "active" && bot.readiness && !bot.readiness.is_ready) {
    return t("aiAgents.status.activeBlocked");
  }
  return t(`aiAgents.status.${bot.status}`);
}

export function getOnboardingSteps({
  botId,
  profileReady,
  hasActiveChannel,
  hasKnowledge,
  t,
}: {
  botId: Id;
  profileReady: boolean;
  hasActiveChannel: boolean;
  hasKnowledge: boolean;
  t: (key: string) => string;
}): OnboardingStep[] {
  return [
    { done: profileReady, title: t("aiAgents.section.profile"), text: t(profileReady ? "aiAgents.checklist.profile" : "aiAgents.checklist.fillProfile"), href: `/app/ai-agents/${botId}/profile` },
    { done: hasKnowledge, title: t("aiAgents.section.knowledgeSimple"), text: t(hasKnowledge ? "aiAgents.checklist.knowledge" : "aiAgents.checklist.addKnowledge"), href: `/app/ai-agents/${botId}/knowledge` },
    { done: hasActiveChannel, title: t("aiAgents.section.channels"), text: t(hasActiveChannel ? "aiAgents.checklist.channel" : "aiAgents.checklist.connectChannel"), href: `/app/ai-agents/${botId}/channels` },
  ];
}

export function sectionsForAgent(scenario?: string) {
  return scenario === "crm" ? [
    { id: "work" as const, labelKey: "aiScenario.work", titleKey: "aiScenario.work", icon: MessageSquareText },
    { id: "analytics" as const, labelKey: "aiScenario.analytics", titleKey: "aiScenario.analytics", icon: BookOpen },
    ...sections.filter(section => !["channels", "overview"].includes(section.id))] : sections;
}

export function defaultAgentSection(bot: BotType): AgentSection {
  if (!bot.readiness?.profile_ready) return "profile";
  return bot.scenario === "crm" ? "work" : "overview";
}

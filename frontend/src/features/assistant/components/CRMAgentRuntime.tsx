import { useMutation, useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { aiApi } from "../../../api/ai";
import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import { hasPermission } from "../../../lib/permissions";
import type { Bot } from "../../../types";
import { useAuth } from "../../auth/AuthProvider";
import { AgentConversationPanel } from "./AgentConversationPanel";
import { CRMCommandPanel } from "./CRMCommandPanel";
import type { CRMEntity } from "../../../api/aiCRM";
import { AIHistoryPanel } from "./AIHistoryPanel";

export function CRMAgentRuntime({ bot, section, dirty = false }: { bot: Pick<Bot, "id" | "business" | "status" | "readiness">; section: "work" | "analytics"; dirty?: boolean }) {
  const { t } = useI18n();
  const { user } = useAuth();
  const allowed = hasPermission(user, bot.business, section === "work" ? "ai_assistant" : "ai_analyst", "view");
  if (!allowed) return <ErrorState message={t("aiScenario.noAccess")} />;
  if (section === "analytics" && bot.readiness?.analytics_enabled === false) return <div role="status" className="space-y-3 py-6 text-sm text-platforma-subtle">
    <p>{t("aiAgents.readiness.analyticsDisabled")}</p>
    {hasPermission(user, bot.business, "ai_automation", "manage") && <Link className="platforma-focus-ring underline" to={`/app/ai-agents/${bot.id}/actions`}>{t("aiAgents.section.actions")}</Link>}
  </div>;
  if (bot.status !== "active") return <p role="status" className="py-6 text-sm text-platforma-subtle">{t("aiScenario.activateFirst")}</p>;
  if (!bot.readiness?.is_ready) return <p role="status" className="py-6 text-sm text-platforma-subtle">{t(bot.readiness?.provider && !bot.readiness.provider.configuration_ready
    ? `aiAgents.readiness.provider.${bot.readiness.provider.state}` : "aiScenario.activateFirst")}</p>;
  if (dirty) return <p role="status" className="py-6 text-sm text-platforma-subtle">{t("aiScenario.saveFirst")}</p>;
  return <div className="space-y-6">
    <AgentConversationPanel key={`${bot.id}:${section}`} businessId={bot.business} agentId={bot.id} mode={section} />
    {section === "work" && <CRMRecordControls bot={bot} />}
    {section === "analytics" && <><AIHistoryPanel businessId={bot.business} agentId={bot.id} conversationMode /><CRMEventBrief bot={bot} /></>}
  </div>;
}

function CRMRecordControls({ bot }: { bot: Pick<Bot, "id" | "business"> }) {
  const { t } = useI18n();
  const { user } = useAuth();
  const status = useQuery({ queryKey: ["ai-assistant-status", bot.business, bot.id], queryFn: () => aiApi.assistantStatus(bot.business, bot.id) });
  if (status.isLoading) return <LoadingState />;
  if (status.error) return <ErrorState error={status.error} message={t("aiAgents.readiness.toolsError")}
    action={<Button variant="secondary" onClick={() => void status.refetch()}>{t("common.retry")}</Button>} />;
  const data = status.data;
  if (!data) return null;
  if (!data.ready) return <div className="space-y-3"><p role="status" className="text-sm text-platforma-subtle">{t("aiAgents.readiness.toolsUnavailable")}</p>
    <Button variant="secondary" onClick={() => void status.refetch()}>{t("common.retry")}</Button></div>;
  if (!data.sources.length || (data.tools !== null && !data.tools.includes("crm_read"))) return <p role="status" className="text-sm text-platforma-subtle">{t("aiAgents.readiness.noTools")}</p>;
  return <details className="rounded-xl border border-platforma-border p-4"><summary className="cursor-pointer text-sm font-semibold">{t("aiCRM.title")}</summary>
    <div className="mt-4"><CRMCommandPanel key={data.sources.join(",")} businessId={bot.business} agentId={bot.id} allowedSources={data.sources as CRMEntity[]}
      canSuggest={hasPermission(user, bot.business, "ai_pipeline", "suggest") && (data.tools === null || data.tools.some(tool => ["crm_create", "crm_update", "crm_archive", "crm_restore", "crm_transition"].includes(tool)))}
      canExecute={hasPermission(user, bot.business, "ai_pipeline", "execute") && hasPermission(user, bot.business, "ai_pipeline", "approve")} /></div>
  </details>;
}

function CRMEventBrief({ bot }: { bot: Pick<Bot, "id" | "business"> }) {
  const { t } = useI18n();
  const brief = useMutation({ mutationFn: () => aiApi.analystBrief({ business: bot.business, agent: bot.id }) });
  return <section className="space-y-3">
    <Button variant="secondary" onClick={() => brief.mutate()} isLoading={brief.isPending}>{t("aiScenario.eventBrief")}</Button>
    {brief.error && <ErrorState error={brief.error} message={getApiErrorMessage(brief.error)} />}
    {brief.data && <>
      {brief.data.provider_state !== "live" && <p role="status" className="text-sm text-platforma-subtle">{t(`aiScenario.brief.${brief.data.provider_state}`)}</p>}
      {brief.data.insights.map(insight => <article key={insight.id} className="rounded-xl border border-platforma-border p-4"><h3 className="text-sm font-semibold">{insight.title}</h3><p className="mt-1 text-sm">{insight.summary}</p></article>)}
      {brief.data.actions.map(action => <Link key={action.id} to={action.href} className="block text-sm underline">{action.label}</Link>)}
      {brief.data.sources.length > 0 && <details><summary className="cursor-pointer text-sm">{t("aiScenario.sources")}</summary><ul className="mt-2 space-y-2 text-xs text-platforma-subtle">{brief.data.sources.map(source => <li key={source.id}>{source.label}: {source.summary}</li>)}</ul></details>}
    </>}
  </section>;
}

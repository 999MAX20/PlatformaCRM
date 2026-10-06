import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { aiApi, AIChatStatusError } from "../../../api/ai";
import type { CRMEntity } from "../../../api/aiCRM";
import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { Textarea } from "../../../components/ui/Textarea";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import { hasPermission } from "../../../lib/permissions";
import type { Bot } from "../../../types";
import { useAuth } from "../../auth/AuthProvider";
import { CRMCommandPanel } from "./CRMCommandPanel";
import { AIHistoryPanel } from "./AIHistoryPanel";

export function CRMAgentRuntime({ bot, section, dirty = false }: { bot: Pick<Bot, "id" | "business" | "status" | "readiness">; section: "work" | "analytics"; dirty?: boolean }) {
  const { t } = useI18n();
  const { user } = useAuth();
  const allowed = hasPermission(user, bot.business, section === "work" ? "ai_assistant" : "ai_analyst", "view");
  if (!allowed) return <ErrorState message={t("aiScenario.noAccess")} />;
  if (bot.status !== "active" || !bot.readiness?.is_ready) return <p role="status" className="py-6 text-sm text-platforma-subtle">{t("aiScenario.activateFirst")}</p>;
  if (dirty) return <p role="status" className="py-6 text-sm text-platforma-subtle">{t("aiScenario.saveFirst")}</p>;
  return section === "work" ? <CRMWork bot={bot} /> : <div className="space-y-5"><AIHistoryPanel businessId={bot.business} agentId={bot.id} /><CRMEventBrief bot={bot} /></div>;
}

function CRMWork({ bot }: { bot: Pick<Bot, "id" | "business"> }) {
  const { t } = useI18n();
  const { user } = useAuth();
  const [message, setMessage] = useState("");
  const canAsk = hasPermission(user, bot.business, "ai_assistant", "suggest");
  const status = useQuery({ queryKey: ["ai-assistant-status", bot.business, bot.id], queryFn: () => aiApi.assistantStatus(bot.business, bot.id) });
  const chat = useMutation({ mutationFn: () => aiApi.assistantChat({ business: bot.business, agent: bot.id, message }) });
  return <div className="space-y-5">
    {status.isLoading ? <LoadingState /> : status.error ? <ErrorState error={status.error} action={<Button onClick={() => status.refetch()}>{t("common.retry")}</Button>} /> : <>
      {!status.data?.ready && <p role="status" className="text-sm text-platforma-subtle">{t("aiScenario.unavailable")}</p>}
      {status.data?.mode === "mock" && <p className="text-sm text-platforma-subtle">{t("aiAssistant.mockModeText")}</p>}
      <form className="space-y-3" onSubmit={event => { event.preventDefault(); if (canAsk && message.trim() && !chat.isPending && status.data?.ready) chat.mutate(); }}>
        <Textarea label={t("aiAssistant.questionLabel")} placeholder={t("aiAssistant.questionPlaceholder")} value={message} disabled={!canAsk || chat.isPending} onChange={event => setMessage(event.target.value)} />
        <Button type="submit" variant="ai" disabled={!canAsk || !message.trim() || !status.data?.ready} isLoading={chat.isPending}>{t("aiAssistant.ask")}</Button>
      </form>
    </>}
    {chat.error && <ErrorState error={chat.error} message={chat.error instanceof AIChatStatusError ? t(chat.error.messageKey) : getApiErrorMessage(chat.error)} />}
    {chat.data && <div className="space-y-3 rounded-xl border border-platforma-border p-4" aria-live="polite"><p className="whitespace-pre-wrap text-sm">{chat.data.answer}</p>{chat.data.sources.length > 0 && <ul className="space-y-1 text-xs text-platforma-subtle">{chat.data.sources.map(source => <li key={source.id}>{source.label}</li>)}</ul>}</div>}
    {status.data && status.data.sources.length > 0 && (status.data.tools === null || status.data.tools.includes("crm_read")) && <CRMCommandPanel
      key={status.data.sources.join(",")} businessId={bot.business} agentId={bot.id} allowedSources={status.data.sources as CRMEntity[]}
      canSuggest={hasPermission(user, bot.business, "ai_pipeline", "suggest") && (status.data.tools === null || status.data.tools.some(tool => ["crm_create", "crm_update", "crm_archive", "crm_restore", "crm_transition"].includes(tool)))}
      canExecute={hasPermission(user, bot.business, "ai_pipeline", "execute") && hasPermission(user, bot.business, "ai_pipeline", "approve")} />}
  </div>;
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

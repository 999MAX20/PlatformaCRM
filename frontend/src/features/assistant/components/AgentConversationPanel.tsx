import { useRef, useState } from "react";
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router";
import { MessageSquarePlus, Send, Square, RotateCcw } from "lucide-react";
import { aiConversationsApi, type AgentTurn, type ConversationMode } from "../../../api/aiConversations";
import { aiApi } from "../../../api/ai";
import { Button } from "../../../components/ui/Button";
import { Select } from "../../../components/ui/Select";
import { Input } from "../../../components/ui/Input";
import { Textarea } from "../../../components/ui/Textarea";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useActionConfirm } from "../../../components/actions/ActionConfirmProvider";
import { useI18n } from "../../../lib/i18n";
import { hasPermission } from "../../../lib/permissions";
import type { Id } from "../../../types";
import { useAuth } from "../../auth/AuthProvider";
import { AgentTurnCard } from "./AgentTurnCard";

const running = (turn?: AgentTurn) => turn?.status === "preparing" || turn?.status === "executing";

export function AgentConversationPanel({ businessId, agentId, mode }: { businessId: Id; agentId: Id; mode: ConversationMode }) {
  const { t } = useI18n();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const confirm = useActionConfirm();
  const [params, setParams] = useSearchParams();
  const selected = params.get("agent_thread") || "";
  const [message, setMessage] = useState("");
  const [archived, setArchived] = useState(false);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const requestKey = useRef<string | null>(null);
  const retryKeys = useRef(new Map<Id, string>());
  const input = useRef<HTMLTextAreaElement>(null);
  const canAsk = hasPermission(user, businessId, mode === "analytics" ? "ai_analyst" : "ai_assistant", mode === "analytics" ? "view" : "suggest");
  const canExecute = hasPermission(user, businessId, "ai_pipeline", "approve") && hasPermission(user, businessId, "ai_pipeline", "execute");
  const status = useQuery({ queryKey: ["ai-assistant-status", businessId, agentId, mode], queryFn: () => aiApi.assistantStatus(businessId, agentId, mode) });
  const list = useInfiniteQuery({ queryKey: ["agent-conversations", businessId, agentId, archived], initialPageParam: 0,
    queryFn: ({ pageParam }) => aiConversationsApi.list({ business: businessId, agent: agentId, archived, offset: pageParam }),
    getNextPageParam: page => page.next_offset ?? undefined });
  const conversations = [...new Map((list.data?.pages.flatMap(page => page.results) || []).map(item => [item.id, item])).values()];
  const history = useInfiniteQuery({ queryKey: ["agent-conversation", businessId, agentId, selected], enabled: Boolean(selected),
    initialPageParam: undefined as number | undefined,
    queryFn: async ({ pageParam }) => {
      const page = await aiConversationsApi.get(selected, pageParam);
      if (page.conversation.business !== businessId || page.conversation.agent !== agentId) throw new Error(t("aiScenario.noAccess"));
      return page;
    },
    getNextPageParam: page => page.has_more ? page.next_before ?? undefined : undefined,
    refetchInterval: query => running(query.state.data?.pages[0]?.turns.at(-1)) ? 1500 : false });
  const thread = history.isError ? undefined : history.data?.pages[0]?.conversation;
  const turns = [...new Map((history.isError ? [] : history.data?.pages.flatMap(page => page.turns) || []).map(turn => [turn.id, turn])).values()].sort((a, b) => a.sequence - b.sequence);
  const latest = turns.at(-1);
  const select = (id: string) => {
    setParams(current => { const next = new URLSearchParams(current); if (id) next.set("agent_thread", id); else next.delete("agent_thread"); return next; }, { replace: true });
    setMessage(""); requestKey.current = null;
  };
  const refresh = async () => {
    await Promise.all([queryClient.invalidateQueries({ queryKey: ["agent-conversation", businessId, agentId] }),
      queryClient.invalidateQueries({ queryKey: ["agent-conversations", businessId, agentId] })]);
  };
  const create = useMutation({ mutationFn: () => aiConversationsApi.create({ business: businessId, agent: agentId, mode }),
    onSuccess: thread => { select(thread.id); setArchived(false); }, onSettled: refresh });
  const send = useMutation({ mutationFn: async () => {
    let id = selected;
    if (!id) {
      const created = await aiConversationsApi.create({ business: businessId, agent: agentId, mode });
      id = created.id;
      setParams(current => { const next = new URLSearchParams(current); next.set("agent_thread", id); return next; }, { replace: true });
    }
    requestKey.current ??= crypto.randomUUID();
    return aiConversationsApi.send(id, { message: message.trim(), idempotency_key: requestKey.current, mode,
      ...(mode === "analytics" && start && end ? { period: { start, end } } : {}) });
  }, onSuccess: () => { setMessage(""); requestKey.current = null; input.current?.focus(); }, onSettled: refresh });
  const action = useMutation({ mutationFn: async ({ kind, turn }: { kind: "confirm" | "cancel" | "retry"; turn: AgentTurn }) => {
    if (kind === "cancel") return aiConversationsApi.cancel(selected, turn.id);
    if (kind === "retry") {
      const key = retryKeys.current.get(turn.id) || crypto.randomUUID(); retryKeys.current.set(turn.id, key);
      return aiConversationsApi.retry(selected, turn.id, key);
    }
    return aiConversationsApi.confirm(selected, turn.id, thread!.revision,
      turn.actions.filter(item => item.status === "suggested").map(item => ({ id: item.id, fingerprint: item.fingerprint })));
  }, onSuccess: async (_, variables) => {
    retryKeys.current.delete(variables.turn.id);
    if (variables.kind === "confirm") await Promise.all(["ai-crm-records", "ai-history", "clients", "leads", "deals", "tasks", "appointments", "activity-events", "notifications"].map(key => queryClient.invalidateQueries({ queryKey: [key] })));
  }, onSettled: refresh });
  const manage = useMutation({ mutationFn: (kind: "reset" | "archive") => kind === "reset" ? aiConversationsApi.reset(selected) : aiConversationsApi.archive(selected, !thread?.is_archived), onSettled: refresh });
  const busy = send.isPending || create.isPending || action.isPending || manage.isPending;
  const error = send.error || action.error || manage.error || create.error;
  const changeThread = async (id: string) => {
    if (message.trim()) {
      const result = await confirm({ title: t("agentChat.leaveDraft"), description: t("agentChat.leaveDraftText"), confirmLabel: t("agentChat.switch"), tone: "neutral" });
      if (!result.confirmed) return;
    }
    select(id); send.reset(); action.reset(); manage.reset();
  };
  return <section className="space-y-4" aria-label={t("agentChat.title")}>
    <div className="flex flex-wrap items-end gap-3">
      <div className="min-w-0 flex-1"><Select label={t("agentChat.history")} value={selected} disabled={busy} onChange={event => { void changeThread(event.target.value); }}
        options={[{ value: "", label: t("agentChat.new") }, ...conversations.map(item => ({ value: item.id, label: item.title || t("agentChat.untitled") })),
          ...(selected && !conversations.some(item => item.id === selected) ? [{ value: selected, label: thread?.title || t("agentChat.untitled") }] : [])]} /></div>
      {list.hasNextPage && <Button variant="ghost" isLoading={list.isFetchingNextPage} onClick={() => list.fetchNextPage()}>{t("agentChat.moreThreads")}</Button>}
      <Button variant="secondary" disabled={busy || !canAsk || Boolean(message.trim())} onClick={() => create.mutate()}><MessageSquarePlus size={16} aria-hidden="true" />{t("agentChat.new")}</Button>
      <label className="flex min-h-10 items-center gap-2 text-sm"><input type="checkbox" checked={archived} disabled={busy} onChange={event => setArchived(event.target.checked)} />{t("agentChat.archived")}</label>
    </div>
    {list.error && <ErrorState error={list.error} action={<Button variant="secondary" onClick={() => list.refetch()}>{t("common.retry")}</Button>} />}
    {thread && <div className="flex flex-wrap items-center gap-2 text-xs text-platforma-subtle">
      <span>{t(thread.memory_enabled ? "agentChat.memoryOn" : "agentChat.memoryOff")}</span>
      <Button size="sm" variant="ghost" disabled={busy} onClick={async () => {
        const result = await confirm({ title: t("agentChat.reset"), description: t("agentChat.resetText"), confirmLabel: t("agentChat.reset"), tone: "neutral" });
        if (result.confirmed) manage.mutate("reset");
      }}>{t("agentChat.reset")}</Button>
      <Button size="sm" variant="ghost" disabled={busy} onClick={async () => {
        const result = await confirm({ title: t(thread.is_archived ? "agentChat.restore" : "agentChat.archive"), description: t("agentChat.archiveText"), confirmLabel: t("actions.confirm"), tone: "neutral" });
        if (result.confirmed) manage.mutate("archive");
      }}>{t(thread.is_archived ? "agentChat.restore" : "agentChat.archive")}</Button>
    </div>}
    {history.isLoading && selected && <LoadingState />}
    {history.error && <ErrorState error={history.error} action={<Button variant="secondary" onClick={() => history.refetch()}>{t("common.retry")}</Button>} />}
    {history.hasNextPage && <Button variant="ghost" isLoading={history.isFetchingNextPage} onClick={() => history.fetchNextPage()}>{t("agentChat.older")}</Button>}
    <div role="log" className="space-y-5" aria-label={t("agentChat.messages")}>
      {turns.map(turn => <AgentTurnCard key={turn.id} turn={turn} busy={busy} canExecute={canExecute && !thread?.is_archived} isLatest={turn.id === latest?.id}
        onConfirm={async () => {
          const result = await confirm({ title: t("aiCRM.confirmTitle"), description: t("aiCRM.confirmText"), confirmLabel: t("actions.confirm"), tone: turn.actions.some(item => item.tool_name === "crm_archive") ? "danger" : "ai" });
          if (result.confirmed) action.mutate({ kind: "confirm", turn });
        }} onCancel={() => action.mutate({ kind: "cancel", turn })} onRetry={() => action.mutate({ kind: "retry", turn })} />)}
    </div>
    {error && <ErrorState error={error} />}
    {status.error && <ErrorState error={status.error} action={<Button variant="secondary" onClick={() => status.refetch()}>{t("common.retry")}</Button>} />}
    {status.data?.mode === "mock" && <p role="status" className="text-sm text-platforma-subtle">{t("aiAssistant.mockModeText")}</p>}
    {!history.isError && !thread?.is_archived && <form className="space-y-3 border-t border-platforma-border pt-4" onSubmit={event => { event.preventDefault(); if (!busy && !running(latest) && canAsk && message.trim() && status.data?.ready) send.mutate(); }}>
      {mode === "analytics" && <div className="grid gap-3 sm:grid-cols-2">
        <Input type="date" label={t("agentChat.periodStart")} value={start} max={end || undefined} disabled={busy} onChange={event => { setStart(event.target.value); requestKey.current = null; }} />
        <Input type="date" label={t("agentChat.periodEnd")} value={end} min={start || undefined} disabled={busy} onChange={event => { setEnd(event.target.value); requestKey.current = null; }} />
      </div>}
      <Textarea ref={input} label={t(mode === "analytics" ? "aiHistory.question" : "agentChat.message")} placeholder={t(mode === "analytics" ? "agentChat.analyticsPlaceholder" : "agentChat.placeholder")} value={message} maxLength={4000} disabled={!canAsk || busy}
        onChange={event => { setMessage(event.target.value); requestKey.current = null; send.reset(); }} />
      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" variant="ai" isLoading={send.isPending} disabled={!canAsk || busy || running(latest) || !message.trim() || !status.data?.ready || Boolean(mode === "analytics" && (Boolean(start) !== Boolean(end) || start > end))}>
          <Send size={16} aria-hidden="true" />{t("agentChat.send")}
        </Button>
        {running(latest) && <><span role="status" className="text-sm text-platforma-subtle">{t(`agentChat.status.${latest!.status}`)}</span><Button type="button" variant="secondary" disabled={busy} onClick={() => action.mutate({ kind: "cancel", turn: latest! })}><Square size={14} aria-hidden="true" />{t("agentChat.stop")}</Button></>}
        {send.error && <Button type="button" variant="secondary" disabled={busy || !message.trim()} onClick={() => send.mutate()}><RotateCcw size={14} aria-hidden="true" />{t("common.retry")}</Button>}
      </div>
      {status.data && !status.data.ready && <p role="status" className="text-sm text-platforma-subtle">{t("aiScenario.unavailable")}</p>}
    </form>}
  </section>;
}

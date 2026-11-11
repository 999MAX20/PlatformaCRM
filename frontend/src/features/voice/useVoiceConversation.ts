import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { aiConversationsApi, type AgentTurn } from "../../api/aiConversations";
import type { Id } from "../../types";

export function useVoiceConversation(userId: Id, businessId: Id, initialConversation?: string) {
  const storageKey = `voice-thread:v2:${userId}:${businessId}`;
  const [selected, setSelected] = useState(() => { if (initialConversation !== undefined) return initialConversation; try { return sessionStorage.getItem(storageKey) || ""; } catch { return ""; } });
  useEffect(() => {
    if (initialConversation === undefined) return;
    try { if (initialConversation) sessionStorage.setItem(storageKey, initialConversation); else sessionStorage.removeItem(storageKey); } catch { /* Session storage is optional. */ }
  }, [initialConversation, storageKey]);
  const selectedRef = useRef(selected);
  const alive = useRef(true);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  const client = useQueryClient();
  const history = useQuery({ queryKey: ["voice-conversation", userId, businessId, selected], enabled: Boolean(selected), retry: false,
    queryFn: async () => {
      const page = await aiConversationsApi.get(selected);
      if (page.conversation.business !== businessId || page.conversation.kind !== "voice" || page.conversation.agent !== null) throw new Error("voice_context_unavailable");
      return page;
    }, refetchInterval: query => ["preparing", "executing"].includes(query.state.data?.turns.at(-1)?.status || "") ? 1200 : false });
  const turns = history.isError ? [] : history.data?.turns || [];
  const latest = turns.at(-1);
  const refreshedTurn = useRef<string>("");
  useEffect(() => {
    if (!latest || latest.status !== "completed" || !latest.actions.some(action => action.status === "executed")) return;
    const key = `${selected}:${latest.id}:${latest.updated_at}`;
    if (refreshedTurn.current === key) return;
    refreshedTurn.current = key;
    void Promise.all(["clients", "tasks", "appointments", "calendar", "records", "visit-plans", "voice-history", "activity-events", "notifications"].map(name => client.invalidateQueries({ queryKey: [name] })));
  }, [latest, selected, client]);
  const request = useRef<{ message: string; context: string; key: string } | null>(null);
  const retryKeys = useRef(new Map<Id, string>());
  const refresh = () => client.invalidateQueries({ queryKey: ["voice-conversation", userId, businessId] });
  function select(id: string) {
    selectedRef.current = id;
    try { if (id) sessionStorage.setItem(storageKey, id); else sessionStorage.removeItem(storageKey); } catch { /* Private history remains available on the server. */ }
    if (alive.current) setSelected(id);
  }
  const send = useMutation({ mutationFn: async ({ message, currentEntity, currentBranch }: { message: string; currentBranch?: number; currentEntity?: { entity: "clients" | "tasks" | "appointments"; id: number } }) => {
    let id = selectedRef.current;
    if (!id) {
      id = (await aiConversationsApi.create({ business: businessId, kind: "voice", mode: "work" })).id;
      select(id);
      if (!alive.current) return;
    }
    const context = JSON.stringify({ currentEntity, currentBranch });
    if (request.current?.message !== message || request.current?.context !== context) request.current = { message, context, key: crypto.randomUUID() };
    await aiConversationsApi.send(id, { message, idempotency_key: request.current.key, mode: "work", origin: "voice", execution: "direct", current_entity: currentEntity, current_branch: currentBranch });
    request.current = null;
  }, onSettled: refresh });
  const action = useMutation({ mutationFn: async ({ kind, turn }: { kind: "confirm" | "cancel" | "retry"; turn: AgentTurn }) => {
    if (kind === "cancel") return aiConversationsApi.cancel(selected, turn.id);
    if (kind === "retry") {
      const retryKey = retryKeys.current.get(turn.id) || crypto.randomUUID(); retryKeys.current.set(turn.id, retryKey);
      return aiConversationsApi.retry(selected, turn.id, retryKey);
    }
    if (!history.data || history.isError) throw new Error("voice_context_unavailable");
    return aiConversationsApi.confirm(selected, turn.id, history.data.conversation.revision,
      turn.actions.filter(item => item.status === "suggested").map(item => ({ id: item.id, fingerprint: item.fingerprint })));
  }, onSuccess: async (_, variables) => {
    retryKeys.current.delete(variables.turn.id);
    await Promise.all(["clients", "tasks", "appointments", "calendar", "records", "visit-plans", "voice-history", "activity-events", "notifications"].map(name => client.invalidateQueries({ queryKey: [name] })));
  }, onSettled: refresh });
  return { history, turns, latest, send, action, selected,
    busy: send.isPending || action.isPending || ["preparing", "executing"].includes(latest?.status || ""),
    newConversation: () => { select(""); request.current = null; send.reset(); action.reset(); } };
}

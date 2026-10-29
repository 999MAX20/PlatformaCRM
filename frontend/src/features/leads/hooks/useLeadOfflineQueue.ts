import { useCallback, useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { leadsApi } from "../../../api/leads";
import { normalizeAppError } from "../../../api/appError";
import type { Lead } from "../../../types";
import { tokenStorage } from "../../../lib/storage";
import { readLeadOfflineData, type LeadOfflineScope } from "../../../lib/leadOfflineStorage";
import { enqueueLeadCommand, LEAD_QUEUE_CHANGED, replayLeadCommands, retryBlockedReason, withLeadQueue } from "../../../lib/leadOfflineCommands";
import type { OfflineLeadAction, Translate } from "../types";

export function useLeadOfflineQueue({ scope, onlineLeads, hasFreshData, accessDenied, t, onNotice, onWarning }: {
  scope: LeadOfflineScope | null; onlineLeads: Lead[]; hasFreshData: boolean; accessDenied: boolean;
  t: Translate; onNotice: (message: string | null, tone?: "success" | "info" | "warning" | "danger") => void;
  onWarning: (message: string) => void;
}) {
  const queryClient = useQueryClient();
  const [isOnline, setIsOnline] = useState(() => navigator.onLine);
  const [stored, setStored] = useState(() => ({ identity: scope?.identity, ...readLeadOfflineData(scope) }));
  const [storageError, setStorageError] = useState("");
  const [syncing, setSyncing] = useState(false);
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const generation = tokenStorage.getGeneration();
  const identity = scope?.identity;
  const latest = useRef({ identity, generation, accessDenied, t, onNotice, onWarning });
  latest.current = { identity, generation, accessDenied, t, onNotice, onWarning };
  const isCurrent = useCallback(() => Boolean(mounted.current && scope && !latest.current.accessDenied
    && latest.current.identity === identity && latest.current.generation === generation
    && tokenStorage.getGeneration() === generation && tokenStorage.getUserId() === String(scope.userId)), [scope, identity, generation]);
  const refresh = useCallback(() => {
    if (isCurrent()) setStored({ identity, ...readLeadOfflineData(scope) });
  }, [identity, scope, isCurrent]);
  const reportStorage = useCallback(() => { if (isCurrent()) setStorageError("leads.queueStorageError"); }, [isCurrent]);
  useEffect(() => {
    if (!scope || !accessDenied) return;
    const sameSession = () => latest.current.identity === identity && tokenStorage.getGeneration() === generation
      && tokenStorage.getUserId() === String(scope.userId);
    void withLeadQueue(scope, sameSession, (data, save) => { data.leads = []; data.queue = []; save(); }).catch(() => {});
  }, [scope, accessDenied, identity, generation]);
  useEffect(() => {
    refresh();
    const online = () => setIsOnline(navigator.onLine);
    window.addEventListener("online", online); window.addEventListener("offline", online);
    window.addEventListener("storage", refresh); window.addEventListener(LEAD_QUEUE_CHANGED, refresh);
    return () => {
      window.removeEventListener("online", online); window.removeEventListener("offline", online);
      window.removeEventListener("storage", refresh); window.removeEventListener(LEAD_QUEUE_CHANGED, refresh);
    };
  }, [refresh]);
  useEffect(() => {
    if (!scope || !isCurrent() || !hasFreshData) return;
    void withLeadQueue(scope, isCurrent, (data, save) => {
      data.leads = onlineLeads.filter(lead => lead.business === scope.businessId).slice(0, 50); save();
    }).catch(reportStorage);
  }, [scope, isCurrent, onlineLeads, hasFreshData, reportStorage]);

  const sync = useCallback(async () => {
    if (!scope || !isCurrent() || !navigator.onLine) return;
    setSyncing(true);
    try {
      const count = await replayLeadCommands(scope, isCurrent, item => item.type === "note"
        ? leadsApi.addNote({ id: item.leadId, text: item.text, commandKey: item.commandKey })
        : leadsApi.createTask({ leadId: item.leadId, commandKey: item.commandKey, payload: {
          title: item.title, description: "", assignee: item.assignee ? Number(item.assignee) : null,
          due_at: item.due_at || null, priority: item.priority,
        } }), error => normalizeAppError(error).messageKey);
      if (!isCurrent()) return;
      setStorageError("");
      if (count) {
        latest.current.onNotice(latest.current.t("leads.offlineSynced", { count }), "success");
        await Promise.all(["leads", "tasks", "activity-events", "crm-card"].map(key => queryClient.invalidateQueries({ queryKey: [key] })));
      }
    } catch { reportStorage(); }
    finally { if (isCurrent()) setSyncing(false); }
  }, [scope, isCurrent, queryClient, reportStorage]);
  // A failure remains visible until an explicit retry, never a render-driven loop.
  useEffect(() => { if (isOnline) void sync(); }, [isOnline, sync]);
  useEffect(() => {
    if (scope && !isOnline) latest.current.onWarning(latest.current.t("leads.offlineMode"));
  }, [isOnline, scope]);
  const enqueueOfflineAction = async (action: OfflineLeadAction) => {
    if (!scope || !isCurrent()) throw new Error(t("actions.errorUnauthenticated"));
    try { await enqueueLeadCommand(scope, isCurrent, action); setStorageError(""); }
    catch { reportStorage(); throw new Error(t("leads.queueStorageError")); }
    latest.current.onNotice(t("leads.offlineQueued"), "info");
  };
  const recoverOfflineAction = async (id: string, discard = false) => {
    if (!scope || !isCurrent()) return;
    try {
      await withLeadQueue(scope, isCurrent, (data, save) => {
        if (discard) data.queue = data.queue.filter(item => item.id !== id);
        else {
          const item = data.queue.find(item => item.id === id);
          if (item) item.errorKey = retryBlockedReason(item);
        }
        save();
      });
      await sync();
    } catch { reportStorage(); }
  };
  const visible = stored.identity === identity && !accessDenied;
  return { isOnline, syncing, storageError, offlineQueue: visible ? stored.queue : [], cachedLeads: visible ? stored.leads : [], enqueueOfflineAction, recoverOfflineAction };
}

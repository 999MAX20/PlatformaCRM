import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { leadsApi } from "../../../api/leads";
import { tasksApi } from "../../../api/tasks";
import type { Lead } from "../../../types";
import { tokenStorage } from "../../../lib/storage";
import { readLeadOfflineData, writeLeadOfflineData, type LeadOfflineScope } from "../../../lib/leadOfflineStorage";
import { type OfflineLeadAction, type Translate } from "../types";

export function useLeadOfflineQueue({
  scope,
  onlineLeads,
  hasFreshData,
  accessDenied,
  t,
  onNotice,
  onWarning,
}: {
  scope: LeadOfflineScope | null;
  onlineLeads: Lead[];
  hasFreshData: boolean;
  accessDenied: boolean;
  t: Translate;
  onNotice: (message: string | null, tone?: "success" | "info" | "warning" | "danger") => void;
  onWarning: (message: string) => void;
}) {
  const queryClient = useQueryClient();
  const [isOnline, setIsOnline] = useState(() => navigator.onLine);
  const generation = tokenStorage.getGeneration();
  const identity = scope?.identity ?? "";
  const [stored, setStored] = useState(() => ({ identity, ...readLeadOfflineData(scope) }));
  // Reset before rendering children, not one effect later with the previous rows.
  if (stored.identity !== identity) setStored({ identity, ...readLeadOfflineData(scope) });
  const current = useRef({ identity, generation });
  current.current = { identity, generation };
  const isCurrent = () => Boolean(scope
    && current.current.identity === identity && current.current.generation === generation
    && tokenStorage.getGeneration() === generation
    && tokenStorage.getUserId() === String(scope.userId));
  const businessId = scope?.businessId;
  const offlineQueue = stored.identity === identity && !accessDenied ? stored.queue : [];
  const cachedLeads = stored.identity === identity && !accessDenied ? stored.leads : [];
  const [lastSystemNotice, setLastSystemNotice] = useState("");

  useEffect(() => {
    function updateOnlineState() {
      setIsOnline(navigator.onLine);
    }
    window.addEventListener("online", updateOnlineState);
    window.addEventListener("offline", updateOnlineState);
    return () => {
      window.removeEventListener("online", updateOnlineState);
      window.removeEventListener("offline", updateOnlineState);
    };
  }, []);

  useEffect(() => {
    if (!isCurrent()) return;
    if (accessDenied) {
      setStored(value => ({ ...value, leads: [], queue: [] }));
    } else if (hasFreshData) {
      setStored(value => ({ ...value, leads: onlineLeads.filter(lead => lead.business === businessId).slice(0, 50) }));
    }
  }, [identity, generation, businessId, onlineLeads, hasFreshData, accessDenied]);

  useEffect(() => {
    if (scope && stored.identity === identity && isCurrent()) writeLeadOfflineData(scope, stored);
  }, [stored, identity, generation, scope]);

  useEffect(() => {
    if (!isOnline || !businessId || !offlineQueue.length || !isCurrent()) return;
    let cancelled = false;
    async function syncOfflineQueue() {
      const synced: string[] = [];
      for (const item of offlineQueue) {
        if (cancelled || !isCurrent()) return;
        try {
          if (item.type === "note") await leadsApi.addNote({ id: item.leadId, text: item.text });
          if (item.type === "task") {
            const lead = onlineLeads.find((row) => row.id === item.leadId);
            if (!lead) continue;
            await tasksApi.create({
              business: businessId,
              title: item.title,
              description: "",
              client: lead.client,
              lead: lead.id,
              deal: null,
              appointment: null,
              parent_task: null,
              assignee: item.assignee ? Number(item.assignee) : lead.responsible_user || null,
              due_at: new Date(item.due_at).toISOString(),
              reminder_at: null,
              priority: item.priority,
            });
          }
          synced.push(item.id);
        } catch {
          break;
        }
      }
      if (!synced.length || cancelled || !isCurrent()) return;
      setStored(value => value.identity === identity ? { ...value, queue: value.queue.filter(item => !synced.includes(item.id)) } : value);
      onNotice(t("leads.offlineSynced", { count: synced.length }));
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["leads"] }),
        queryClient.invalidateQueries({ queryKey: ["tasks"] }),
        queryClient.invalidateQueries({ queryKey: ["activity-events"] }),
      ]);
    }
    syncOfflineQueue();
    return () => {
      cancelled = true;
    };
  }, [identity, generation, businessId, isOnline, offlineQueue, onNotice, onlineLeads, queryClient, t]);

  useEffect(() => {
    const message = !isOnline ? t("leads.offlineMode") : offlineQueue.length ? t("leads.offlinePending", { count: offlineQueue.length }) : "";
    if (!message || lastSystemNotice === message) return;
    setLastSystemNotice(message);
    onWarning(message);
  }, [isOnline, lastSystemNotice, offlineQueue.length, onWarning, t]);

  function enqueueOfflineAction(action: OfflineLeadAction) {
    if (!isCurrent() || accessDenied) return;
    setStored(value => value.identity === identity ? { ...value, queue: [...value.queue, action].slice(-40) } : value);
    onNotice(t("leads.offlineQueued"));
  }

  return {
    isOnline,
    offlineQueue,
    cachedLeads,
    enqueueOfflineAction,
  };
}

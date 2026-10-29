import type { OfflineLeadAction } from "../features/leads/types";
import { readLeadOfflineData, writeLeadOfflineData, type LeadOfflineData, type LeadOfflineScope } from "./leadOfflineStorage.ts";

export const LEAD_QUEUE_CHANGED = "platforma:lead-queue-changed";
export const RETRY_WINDOW_MS = 3_600_000;

export async function withLeadQueue<T>(scope: LeadOfflineScope, current: () => boolean, operation: (data: LeadOfflineData, save: () => void) => Promise<T> | T) {
  // One lock covers read/modify/write and the in-flight request across tabs.
  if (!navigator.locks) throw new Error("leads.queueStorageError");
  return navigator.locks.request(scope.key, async () => {
    if (!current()) throw new Error("actions.errorUnauthenticated");
    const data = readLeadOfflineData(scope);
    const save = () => {
      if (!current()) throw new Error("actions.errorUnauthenticated");
      if (!writeLeadOfflineData(scope, data)) throw new Error("leads.queueStorageError");
      window.dispatchEvent(new Event(LEAD_QUEUE_CHANGED));
    };
    return operation(data, save);
  });
}

export function retryBlockedReason(item: OfflineLeadAction, now = Date.now()) {
  // Old clients sent unkeyed requests. Their persisted work may already exist.
  if (item.version !== 2) return "leads.queueLegacy";
  if (item.commandKey) {
    const match = /^lead-offline:(\d{13}):[0-9a-f-]{36}$/.exec(item.commandKey);
    if (!match || now - Number(match[1]) > RETRY_WINDOW_MS || Number(match[1]) > now + 60_000) return "leads.queueExpired";
  }
  return undefined;
}

export function enqueueLeadCommand(scope: LeadOfflineScope, current: () => boolean, action: OfflineLeadAction) {
  return withLeadQueue(scope, current, (data, save) => {
    if (data.queue.some(item => item.id === action.id)) return;
    data.queue.push({ ...action, version: 2 });
    // No silent capacity eviction. Quota failure rejects acceptance of new input.
    save();
  });
}

export function replayLeadCommands(scope: LeadOfflineScope, current: () => boolean, send: (item: OfflineLeadAction) => Promise<unknown>, errorKey: (error: unknown) => string) {
  return withLeadQueue(scope, current, async (data, save) => {
    let count = 0;
    for (const queued of [...data.queue]) {
      if (!current() || !navigator.onLine) break;
      if (queued.errorKey) continue;
      const blocked = retryBlockedReason(queued);
      if (blocked) { queued.errorKey = blocked; save(); continue; }
      queued.commandKey ??= `lead-offline:${Date.now()}:${crypto.randomUUID()}`;
      // Durable identity must precede the first external request.
      save();
      try {
        await send(queued);
      } catch (error) {
        if (!current()) break;
        queued.errorKey = errorKey(error);
        save();
        continue;
      }
      if (!current()) break;
      data.queue = data.queue.filter(item => item.id !== queued.id);
      save();
      count++;
    }
    return count;
  });
}

import { useRef, useState } from "react";

import type { Id } from "../../../types";

export function inboxDraftKey(userId: Id, businessId: Id, conversationId: Id) {
  return `zani_inbox_draft:${userId}:${businessId}:${conversationId}`;
}

export function appendReplyDraft(current: string, addition: string) {
  return current ? `${current}\n${addition}` : addition;
}

/** Persist on input, before navigation; never hydrate one dialog into another. */
export function useInboxDraft(userId?: Id, businessId?: Id, conversationId?: Id) {
  const drafts = useRef(new Map<string, string>());
  const [, refresh] = useState(0);
  const key = userId && businessId && conversationId ? inboxDraftKey(userId, businessId, conversationId) : null;
  function read(draftKey: string | null) {
    if (!draftKey) return "";
    if (drafts.current.has(draftKey)) return drafts.current.get(draftKey)!;
    try {
      const stored = sessionStorage.getItem(draftKey);
      if (stored !== null) return stored;
      // Consume the previous business/conversation key once on upgrade, so an
      // already written draft survives and is not imported again by another user.
      const [, , storedBusiness, storedConversation] = draftKey.split(":");
      const legacyKey = `zani_inbox_draft:${storedBusiness}:${storedConversation}`;
      const legacy = sessionStorage.getItem(legacyKey);
      if (legacy !== null) {
        sessionStorage.setItem(draftKey, legacy);
        sessionStorage.removeItem(legacyKey);
        drafts.current.set(draftKey, legacy);
      }
      return legacy || "";
    } catch { return ""; }
  }
  function write(draftKey: string, value: string) {
    drafts.current.set(draftKey, value);
    try {
      if (value) sessionStorage.setItem(draftKey, value);
      else sessionStorage.removeItem(draftKey);
    } catch { /* Keep the in-memory draft when browser storage is unavailable. */ }
    refresh(current => current + 1);
  }
  return {
    draftKey: key,
    draft: read(key),
    setDraft(next: string | ((current: string) => string)) {
      if (key) write(key, typeof next === "function" ? next(read(key)) : next);
    },
    clearSentDraft(sentKey: string | null, text: string) {
      if (!sentKey) return;
      // A late send response must not erase a newer edit or another dialog.
      if (read(sentKey).trim() === text) write(sentKey, "");
    },
  };
}

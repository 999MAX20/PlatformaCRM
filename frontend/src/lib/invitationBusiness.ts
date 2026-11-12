import type { Id } from "../types";

const selected = new Map<string, string>();
const key = (userId: Id) => `platforma:invitation-business:${userId}`;

export function rememberInvitationBusiness(userId: Id, businessId: Id) {
  selected.set(String(userId), String(businessId));
  try { sessionStorage.setItem(key(userId), String(businessId)); } catch { /* Session-only memory also supports restricted storage. */ }
}

export function preferredInvitationBusiness(userId?: Id) {
  if (userId == null) return null;
  try { return sessionStorage.getItem(key(userId)) || selected.get(String(userId)) || null; }
  catch { return selected.get(String(userId)) || null; }
}

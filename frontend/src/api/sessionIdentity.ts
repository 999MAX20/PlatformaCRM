export type SessionIdentity = { userId: string; sessionId: string; expiresAt: number };
export class SessionIdentityChangedError extends Error {}

// UI consistency only. The backend remains responsible for JWT validation.
export function readSessionIdentity(access: string | null): SessionIdentity | null {
  if (!access) return null;
  try {
    const payload = JSON.parse(atob(access.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
    if (payload.user_id == null || typeof payload.exp !== "number") return null;
    return { userId: String(payload.user_id), sessionId: String(payload.sid || ""), expiresAt: payload.exp * 1000 };
  } catch {
    return null;
  }
}

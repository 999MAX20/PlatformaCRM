import { readSessionIdentity } from "../api/sessionIdentity";

const ACCESS_TOKEN_KEY = "ai_smb_access_token";
const USER_EMAIL_KEY = "ai_smb_user_email";

let accessToken: string | null = null;
let sessionGeneration = 0;
let userId: string | null = null;
export const AUTH_EXPIRED_EVENT = "zani:auth-expired";
const channel = typeof BroadcastChannel !== "undefined" ? new BroadcastChannel("platforma:browser-session") : null;

if (channel) channel.onmessage = ({ data }: MessageEvent<unknown>) => {
  if (!data || typeof data !== "object") return;
  const message = data as { type?: string; access?: unknown; sessionId?: string };
  const current = readSessionIdentity(accessToken);
  if (!current) return;
  if (message.type === "access" && typeof message.access === "string") {
    const incoming = readSessionIdentity(message.access);
    if (!incoming || incoming.expiresAt <= Date.now()) return;
    if (incoming.userId === current.userId && incoming.sessionId === current.sessionId) {
      accessToken = message.access; // Memory only; never put credentials in storage.
      return;
    }
  } else if (message.type !== "logout" || message.sessionId !== current.sessionId) return;
  tokenStorage.clear();
  window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
};

export const tokenStorage = {
  getGeneration: () => sessionGeneration,
  getUserId: () => userId,
  setUserId: (id: string | number) => { userId = String(id); },
  getAccess: () => accessToken,
  setAccess: (access: string) => {
    accessToken = access;
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    channel?.postMessage({ type: "access", access });
  },
  broadcastLogout: () => channel?.postMessage({ type: "logout", sessionId: readSessionIdentity(accessToken)?.sessionId }),
  clear: () => {
    sessionGeneration += 1;
    userId = null;
    accessToken = null;
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(USER_EMAIL_KEY);
  },
  getEmail: () => localStorage.getItem(USER_EMAIL_KEY),
  setEmail: (email: string) => localStorage.setItem(USER_EMAIL_KEY, email),
};

import axios, { type AxiosRequestConfig } from "axios";
import { apiClient, handleSessionRecoveryError } from "./client";
import {
  assertCurrentSession,
  sessionCookieRequest,
  loginWithCredentials,
  loginWithSocial,
  requestPasswordReset as requestPasswordResetToken,
  clearRefreshCookie,
  confirmPasswordReset as confirmPasswordResetToken,
  signupOwner as signupOwnerWithCredentials,
  refreshToken,
  confirmMfaEnrollment,
  isMfaPendingResponse,
  startMfaEnrollment,
  verifyMfaLogin,
  type MfaEnrollment,
  type MfaPendingResponse,
  type LoginPayload,
  type OwnerSignupPayload,
  type PasswordResetConfirmPayload,
  type PasswordResetRequestPayload,
  type PasswordResetRequestResponse,
  type SocialLoginPayload,
  type SocialLoginResponse,
  type SocialProvider,
  type SignupOwnerResponse,
  type TokenPair,
} from "./token";
import { tokenStorage } from "../lib/storage";
import type { CurrentUser, LoginHistory } from "../types";

export { confirmMfaEnrollment, isMfaPendingResponse, refreshToken, startMfaEnrollment, verifyMfaLogin };
export type { MfaEnrollment, MfaPendingResponse };
export type { LoginPayload, SocialLoginPayload, SocialLoginResponse, SocialProvider, TokenPair };
export type {
  OwnerSignupPayload,
  PasswordResetConfirmPayload,
  PasswordResetRequestPayload,
  PasswordResetRequestResponse,
  SignupOwnerResponse,
};

// Security mutations replace the HttpOnly cookie too. Use the same queue as
// login/logout, but refresh a rejected credential only after leaving the queue.
// Using apiClient inside the queue would make its interceptor wait on itself.
async function authenticatedCookieRequest<T>(request: (options: AxiosRequestConfig) => Promise<T>) {
  const generation = tokenStorage.getGeneration();
  const send = () => sessionCookieRequest(generation, () => request({
    baseURL: apiClient.defaults.baseURL, timeout: apiClient.defaults.timeout,
    withCredentials: true,
    headers: { Authorization: `Bearer ${tokenStorage.getAccess() || ""}` },
  }));
  try {
    return await send();
  } catch (error) {
    if (!axios.isAxiosError(error) || error.response?.status !== 401) throw error;
    assertCurrentSession(generation);
    try {
      await refreshToken();
      assertCurrentSession(generation);
      return send();
    } catch (refreshError) {
      if (generation === tokenStorage.getGeneration()) handleSessionRecoveryError(refreshError);
      throw refreshError;
    }
  }
}

export async function login(payload: LoginPayload) {
  return loginWithCredentials(payload);
}

export async function socialLogin(payload: SocialLoginPayload) {
  return loginWithSocial(payload);
}

export async function signupOwner(payload: OwnerSignupPayload) {
  return signupOwnerWithCredentials(payload);
}

export async function requestPasswordReset(payload: PasswordResetRequestPayload) {
  return requestPasswordResetToken(payload);
}

export async function confirmPasswordReset(payload: PasswordResetConfirmPayload) {
  return confirmPasswordResetToken(payload);
}

export async function restoreSession() {
  return refreshToken({ activity: document.visibilityState === "visible" && navigator.onLine });
}

export async function recordSessionActivity() {
  await refreshToken({ activity: true });
}

export async function getCurrentUser() {
  const { data } = await apiClient.get<CurrentUser>("/api/auth/me/");
  return data;
}

export async function updateCurrentUser(payload: Partial<Pick<CurrentUser, "full_name" | "phone">> & { preferences?: Partial<NonNullable<CurrentUser["preferences"]>> }) {
  const { data } = await apiClient.patch<CurrentUser>("/api/auth/me/", payload);
  return data;
}

export async function changePassword(payload: { current_password: string; new_password: string; mfa_code?: string }) {
  const { data } = await authenticatedCookieRequest(options => axios.post<{ ok: boolean }>("/api/auth/change-password/", payload, options));
  return data;
}

export async function getCurrentUserLoginHistory() {
  const { data } = await apiClient.get<LoginHistory[]>("/api/auth/login-history/");
  return data;
}

export type AccountSession = {
  id: string;
  user_agent: string;
  ip_address: string | null;
  created_at: string;
  last_seen_at: string;
  is_current: boolean;
};
type AccountSessions = { available: boolean; sessions: AccountSession[]; legacy_count: number };

export async function getAccountSessions() {
  let { data } = await apiClient.get<AccountSessions>("/api/auth/sessions/");
  if (data.available && !data.sessions.some(session => session.is_current)) {
    // Upgrade this browser's pre-rollout refresh token to a tracked session.
    await refreshToken();
    data = (await apiClient.get<AccountSessions>("/api/auth/sessions/")).data;
  }
  return data;
}

export async function revokeAccountSession(id: string, code: string) {
  return (await apiClient.post<{ ok: boolean }>(`/api/auth/sessions/${encodeURIComponent(id)}/revoke/`, { code })).data;
}

export async function requestEmailChange(payload: { new_email: string; current_password: string; mfa_code?: string }) {
  return (await apiClient.post<{ ok: boolean; expires_in: number }>("/api/auth/change-email/request/", payload)).data;
}

export async function confirmEmailChange(code: string) {
  const generation = tokenStorage.getGeneration();
  const { data } = await authenticatedCookieRequest(options => axios.post<{ ok: boolean; email: string; access: string }>("/api/auth/change-email/confirm/", { code }, options));
  assertCurrentSession(generation);
  tokenStorage.setAccess(data.access);
  return data;
}

export type MfaStatus = {
  available: boolean;
  required: boolean;
  enabled: boolean;
  method: "totp" | null;
  confirmed_at: string | null;
  recovery_codes_remaining: number;
  active_sessions: number;
};

export async function getMfaStatus() {
  const { data } = await apiClient.get<MfaStatus>("/api/auth/mfa/status/");
  return data;
}

export async function issueMfaStepUp(code: string) {
  const { data } = await apiClient.post<{ step_up_token: string; expires_in: number }>(
    "/api/auth/mfa/step-up/",
    { code },
  );
  return data;
}

export async function regenerateMfaRecoveryCodes(code: string) {
  const { data } = await apiClient.post<{ recovery_codes: string[] }>("/api/auth/mfa/recovery-codes/", { code });
  return data;
}

export async function disableMfa(payload: { password: string; code: string; reason: string }) {
  const generation = tokenStorage.getGeneration();
  const { data } = await authenticatedCookieRequest(options => axios.post<({ ok: boolean; access: string } | (MfaPendingResponse & { ok: boolean }))>("/api/auth/mfa/disable/", payload, options));
  assertCurrentSession(generation);
  if (isMfaPendingResponse(data)) {
    tokenStorage.clear();
    return data;
  }
  tokenStorage.setAccess(data.access);
  return data;
}

export async function revokeMfaSessions(code: string) {
  const generation = tokenStorage.getGeneration();
  const { data } = await authenticatedCookieRequest(options => axios.post<{ sessions_revoked: number; access: string }>(
    "/api/auth/mfa/sessions/revoke/",
    { code },
    options,
  ));
  assertCurrentSession(generation);
  tokenStorage.setAccess(data.access);
  return data;
}

export function logout() {
  tokenStorage.broadcastLogout();
  tokenStorage.clear();
  void clearRefreshCookie().catch(() => undefined);
}


export type AccountAvatar = { image: string | null };
export async function getAccountAvatar() {
  return (await apiClient.get<AccountAvatar>("/api/auth/me/avatar/")).data;
}
export async function uploadAccountAvatar(file: File, crop?: { x: number; y: number; size: number }) {
  const body = new FormData();
  body.append("file", file);
  if (crop) Object.entries(crop).forEach(([key, value]) => body.append(key, String(value)));
  return (await apiClient.post<AccountAvatar>("/api/auth/me/avatar/", body, { timeout: 75_000, headers: { "Content-Type": "multipart/form-data" } })).data;
}
export async function removeAccountAvatar() {
  return (await apiClient.delete<AccountAvatar>("/api/auth/me/avatar/")).data;
}

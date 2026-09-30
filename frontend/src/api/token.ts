import axios from "axios";

import { tokenStorage } from "../lib/storage";
import type { Business, CurrentUser } from "../types";

const baseURL = import.meta.env.VITE_API_URL || "";
const cookieRequestOptions = { withCredentials: true, timeout: 20_000 };

export function assertCurrentSession(generation: number | undefined) {
  if (generation !== tokenStorage.getGeneration()) {
    throw new axios.CanceledError("Authentication session changed");
  }
}

// Refresh/logout/login responses all mutate the same HttpOnly cookie. Preserve
// their order as well as guarding the in-memory token against late responses.
let cookieOperation: Promise<unknown> = Promise.resolve();
export function sessionCookieRequest<T>(generation: number | undefined, request: () => Promise<T>) {
  const result = cookieOperation.then(async () => {
    if (generation !== undefined) assertCurrentSession(generation);
    const response = await request();
    if (generation !== undefined) assertCurrentSession(generation);
    return response;
  });
  cookieOperation = result.catch(() => undefined);
  return result;
}

function beginLogin() {
  tokenStorage.clear();
  return tokenStorage.getGeneration();
}

function assertSameRefreshUser(access: string) {
  const expected = tokenStorage.getUserId();
  if (expected === null) return;
  let refreshedUser: unknown;
  try {
    const payload = access.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    refreshedUser = JSON.parse(atob(payload)).user_id;
  } catch {
    throw new axios.CanceledError("Invalid refresh identity");
  }
  // Client consistency only; signature validation and authorization remain on
  // the server. A cookie changed in another tab must not silently switch users.
  if (String(refreshedUser) !== expected) throw new axios.CanceledError("Refresh identity changed");
}

export type LoginPayload = {
  email: string;
  password: string;
};

export type TokenPair = {
  access: string;
};

export type MfaPendingResponse = {
  code: "mfa_required" | "mfa_enrollment_required";
  challenge_token: string;
  expires_at: string;
  method: "totp";
};

export type MfaEnrollment = {
  challenge_token: string;
  manual_key: string;
  otpauth_uri: string;
  issuer: string;
  account: string;
  expires_at: string;
};

export type MfaSessionResponse = TokenPair & {
  recovery_codes?: string[];
};

export type SocialProvider = "google" | "apple";

export type SocialLoginPayload = {
  provider: SocialProvider;
  idToken: string;
};

export type SocialLoginResponse = TokenPair & {
  created: boolean;
  provider: SocialProvider;
};

export type OwnerSignupPayload = {
  email: string;
  password: string;
  full_name?: string;
  phone?: string;
  business_name: string;
  business_type: string;
  city?: string;
};

export type SignupOwnerResponse = TokenPair & {
  user: CurrentUser;
  business: Pick<Business, "id" | "name" | "slug">;
};

export type PasswordResetRequestPayload = {
  email: string;
  delivery_channel: "email" | "whatsapp" | "telegram" | "manual";
};

export type PasswordResetRequestResponse = {
  ok: boolean;
  message: string;
  uid?: string;
  token?: string;
  reset_path?: string;
  delivery_channel?: PasswordResetRequestPayload["delivery_channel"];
};

export type PasswordResetConfirmPayload = {
  uid: string;
  token: string;
  password: string;
};

export async function loginWithCredentials(payload: LoginPayload) {
  const generation = beginLogin();
  const { data } = await sessionCookieRequest(generation, () => axios.post<TokenPair | MfaPendingResponse>(`${baseURL}/api/auth/token/`, payload, cookieRequestOptions));
  assertCurrentSession(generation);
  if (isMfaPendingResponse(data)) return data;
  tokenStorage.setAccess(data.access);
  tokenStorage.setEmail(payload.email);
  return data;
}

export async function loginWithSocial(payload: SocialLoginPayload) {
  const generation = beginLogin();
  const { data } = await sessionCookieRequest(generation, () => axios.post<SocialLoginResponse | MfaPendingResponse>(`${baseURL}/api/auth/social/`, {
    provider: payload.provider,
    id_token: payload.idToken,
  }, cookieRequestOptions));
  assertCurrentSession(generation);
  if (isMfaPendingResponse(data)) return data;
  tokenStorage.setAccess(data.access);
  return data;
}

export async function signupOwner(payload: OwnerSignupPayload) {
  const generation = beginLogin();
  const { data } = await sessionCookieRequest(generation, () => axios.post<SignupOwnerResponse | MfaPendingResponse>(`${baseURL}/api/auth/signup/owner/`, payload, cookieRequestOptions));
  assertCurrentSession(generation);
  if (isMfaPendingResponse(data)) return data;
  tokenStorage.setAccess(data.access);
  tokenStorage.setEmail(payload.email);
  return data;
}

export async function requestPasswordReset(payload: PasswordResetRequestPayload) {
  const { data } = await axios.post<PasswordResetRequestResponse>(`${baseURL}/api/auth/password-reset/request/`, payload);
  return data;
}

export async function confirmPasswordReset(payload: PasswordResetConfirmPayload) {
  const generation = tokenStorage.getGeneration();
  const { data } = await sessionCookieRequest(generation, () => axios.post<{ ok: boolean }>(
    `${baseURL}/api/auth/password-reset/confirm/`,
    payload,
    cookieRequestOptions,
  ));
  return data;
}

let refreshSession: { generation: number; promise: Promise<string> } | null = null;

export function refreshToken() {
  const generation = tokenStorage.getGeneration();
  if (refreshSession?.generation === generation) return refreshSession.promise;
  const promise = sessionCookieRequest(generation, () => axios
      .post<{ access: string }>(
        `${baseURL}/api/auth/token/refresh/`,
        {},
        cookieRequestOptions,
      ))
      .then(({ data }) => {
        assertCurrentSession(generation);
        assertSameRefreshUser(data.access);
        tokenStorage.setAccess(data.access);
        return data.access;
      })
      .finally(() => {
        if (refreshSession?.generation === generation) refreshSession = null;
      });
  refreshSession = { generation, promise };
  return promise;
}

export async function clearRefreshCookie() {
  await sessionCookieRequest(undefined, () => axios.post(`${baseURL}/api/auth/logout/`, {}, cookieRequestOptions));
}

export function isMfaPendingResponse(value: unknown): value is MfaPendingResponse {
  if (!value || typeof value !== "object") return false;
  const code = (value as { code?: string }).code;
  return code === "mfa_required" || code === "mfa_enrollment_required";
}

const pendingMfaEnrollmentRequests = new Map<string, Promise<MfaEnrollment>>();

export function startMfaEnrollment(challengeToken?: string) {
  if (challengeToken) {
    const pendingRequest = pendingMfaEnrollmentRequests.get(challengeToken);
    if (pendingRequest) return pendingRequest;
  }

  const request = axios.post<MfaEnrollment>(
    `${baseURL}/api/auth/mfa/enrollment/start/`,
    challengeToken ? { challenge_token: challengeToken } : {},
    { withCredentials: true, headers: tokenStorage.getAccess() ? { Authorization: `Bearer ${tokenStorage.getAccess()}` } : undefined },
  ).then(({ data }) => data);

  if (challengeToken) {
    pendingMfaEnrollmentRequests.set(challengeToken, request);
    void request.catch(() => pendingMfaEnrollmentRequests.delete(challengeToken));
  }
  return request;
}

export async function confirmMfaEnrollment(challengeToken: string, code: string) {
  const generation = tokenStorage.getGeneration();
  try {
    const { data } = await sessionCookieRequest(generation, () => axios.post<MfaSessionResponse>(
      `${baseURL}/api/auth/mfa/enrollment/confirm/`,
      { challenge_token: challengeToken, code },
      cookieRequestOptions,
    ));
    assertCurrentSession(generation);
    tokenStorage.setAccess(data.access);
    return data;
  } finally {
    pendingMfaEnrollmentRequests.delete(challengeToken);
  }
}

export async function verifyMfaLogin(challengeToken: string, code: string) {
  const generation = tokenStorage.getGeneration();
  const { data } = await sessionCookieRequest(generation, () => axios.post<MfaSessionResponse>(
    `${baseURL}/api/auth/mfa/verify/`,
    { challenge_token: challengeToken, code },
    cookieRequestOptions,
  ));
  assertCurrentSession(generation);
  tokenStorage.setAccess(data.access);
  return data;
}

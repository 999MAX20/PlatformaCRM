import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";

import { getAppErrorMessage, normalizeAppError } from "./appError";
import { assertCurrentSession, refreshToken } from "./token";
import { SessionIdentityChangedError } from "./sessionIdentity";
import { getCurrentLanguage, translate } from "../lib/i18n";
import { AUTH_EXPIRED_EVENT, tokenStorage } from "../lib/storage";

const baseURL = import.meta.env.VITE_API_URL || "";
export { AUTH_EXPIRED_EVENT };
export const AUTH_RECOVERY_EVENT = "platforma:auth-recovery";
export const SESSION_EXPIRED_NOTICE_KEY = "zani:session-expired";
export const SESSION_EXPIRED_RETURN_TO_KEY = "zani:session-expired-return-to";

export function isSafeInternalReturnPath(value: string) {
  return /^\/(app|platform)(\/|\?|#|$)/.test(value);
}

function notifyAuthExpired() {
  if (typeof window !== "undefined") {
    try {
      window.sessionStorage.setItem(SESSION_EXPIRED_NOTICE_KEY, "1");
      const returnTo = `${window.location.pathname}${window.location.search}${window.location.hash}`;
      if (isSafeInternalReturnPath(returnTo)) {
        window.sessionStorage.setItem(SESSION_EXPIRED_RETURN_TO_KEY, returnTo);
      }
    } catch {
      // A blocked sessionStorage must not prevent the auth-expired event.
    }
    window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
  }
}

export function isSessionExpiryResponse(error: unknown) {
  if (error instanceof SessionIdentityChangedError) return true;
  if (!axios.isAxiosError(error)) return false;
  return error.response?.status === 400 || error.response?.status === 401;
}

export function expireBrowserSession() {
  tokenStorage.clear();
  notifyAuthExpired();
}

export function handleSessionRecoveryError(error: unknown) {
  if (axios.isCancel(error)) return;
  if (isSessionExpiryResponse(error)) expireBrowserSession();
  else window.dispatchEvent(new CustomEvent(AUTH_RECOVERY_EVENT, { detail: error }));
}

function isAuthEndpoint(url = "") {
  return url.includes("/api/auth/token/") || url.includes("/api/auth/token/refresh/") || url.includes("/api/auth/social/");
}

function isCredentialLoginEndpoint(url = "") {
  return url.includes("/api/auth/token/") && !url.includes("/refresh/");
}

export const apiClient = axios.create({
  baseURL,
  timeout: 20_000,
  headers: {
    "Content-Type": "application/json",
  },
});

export type PaginatedResponse<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
  summary?: unknown;
  facets?: unknown;
};

export function asArray<T>(value: unknown): T[] {
  return Array.isArray(value) ? value as T[] : [];
}

export function unwrapList<T>(data: T[] | PaginatedResponse<T> | { results?: T[] } | null | undefined) {
  if (Array.isArray(data)) return data;
  if (data && Array.isArray(data.results)) return data.results;
  return [];
}

type SessionRequest = InternalAxiosRequestConfig & { _retry?: boolean; _sessionGeneration?: number };

apiClient.interceptors.request.use((config: SessionRequest) => {
  config._sessionGeneration ??= tokenStorage.getGeneration();
  assertCurrentSession(config._sessionGeneration);
  const token = tokenStorage.getAccess();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => { throw error; }, { synchronous: true });

apiClient.interceptors.response.use(
  (response) => {
    assertCurrentSession((response.config as SessionRequest)._sessionGeneration);
    return response;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as SessionRequest | undefined;
    if (!originalRequest) return Promise.reject(error);
    assertCurrentSession(originalRequest._sessionGeneration);
    if (error.response?.status !== 401 || originalRequest._retry || !originalRequest.headers.Authorization || isAuthEndpoint(originalRequest.url || "")) {
      return Promise.reject(error);
    }

    originalRequest._retry = true;
    try {
      const access = await refreshToken();
      assertCurrentSession(originalRequest._sessionGeneration);
      originalRequest.headers.Authorization = `Bearer ${access}`;
      return apiClient(originalRequest);
    } catch (refreshError) {
      if (originalRequest._sessionGeneration === tokenStorage.getGeneration()) handleSessionRecoveryError(refreshError);
      return Promise.reject(refreshError);
    }
  },
);

export function getApiErrorMessage(
  error: unknown,
  translator: (key: string) => string = (key) => translate(getCurrentLanguage(), key),
) {
  return getAppErrorMessage(error, translator);
}

export function getLoginErrorMessage(
  error: unknown,
  translator: (key: string) => string = (key) => translate(getCurrentLanguage(), key),
) {
  const normalized = normalizeAppError(error);
  if (normalized.category === "authentication" && axios.isAxiosError(error)) {
    if (isCredentialLoginEndpoint(error.config?.url || "")) {
      return translator("auth.invalidCredentials");
    }
    return translator("auth.loginUnavailable");
  }
  return translator(normalized.messageKey);
}

export function hasSessionExpiredNotice() {
  if (typeof window === "undefined") return false;
  try {
    return window.sessionStorage.getItem(SESSION_EXPIRED_NOTICE_KEY) === "1";
  } catch {
    return false;
  }
}

export function clearSessionExpiredNotice() {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.removeItem(SESSION_EXPIRED_NOTICE_KEY);
  } catch {
    // A blocked sessionStorage must not break the login page.
  }
}

export function getSessionExpiredReturnTo() {
  if (typeof window === "undefined") return undefined;
  try {
    const returnTo = window.sessionStorage.getItem(SESSION_EXPIRED_RETURN_TO_KEY) || "";
    return isSafeInternalReturnPath(returnTo) ? returnTo : undefined;
  } catch {
    return undefined;
  }
}

export function clearSessionExpiredReturnTo() {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.removeItem(SESSION_EXPIRED_RETURN_TO_KEY);
  } catch {
    // A blocked sessionStorage must not break authenticated navigation.
  }
}

export function consumeSessionExpiredReturnTo() {
  const returnTo = getSessionExpiredReturnTo();
  clearSessionExpiredReturnTo();
  return returnTo;
}

export function getApiFieldErrors(error: unknown) {
  return normalizeAppError(error).fieldErrors;
}

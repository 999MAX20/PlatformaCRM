import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  AUTH_EXPIRED_EVENT,
  AUTH_RECOVERY_EVENT,
  expireBrowserSession,
  isSessionExpiryResponse,
} from "../../api/client";
import axios from "axios";
import { normalizeAppError } from "../../api/appError";
import { SERVICE_AVAILABLE_EVENT } from "../../api/connectivity";
import { NotificationPortal, NotificationPresence, useConnectionNoticeState } from "../../components/notifications/NotificationHost";
import { Button } from "../../components/ui/Button";
import { ErrorState } from "../../components/ui/StateViews";
import { StatusNotice } from "../../components/ui/StatusNotice";
import { RecoveryDetails } from "../../components/ui/RecoveryDetails";
import { useRecoveryDelay } from "../../components/actions/useRecoveryDelay";
import { useI18n } from "../../lib/i18n";
import { useBrowserSessionActivity } from "./useBrowserSessionActivity";
import {
  getCurrentUser,
  isMfaPendingResponse,
  login as apiLogin,
  logout as apiLogout,
  restoreSession,
  signupOwner as apiSignupOwner,
  socialLogin as apiSocialLogin,
  type OwnerSignupPayload,
  type SocialProvider,
  type MfaPendingResponse,
} from "../../api/auth";
import { assertCurrentSession } from "../../api/token";
import { tokenStorage } from "../../lib/storage";
import type { Business, CurrentUser } from "../../types";

type AuthContextValue = {
  sessionGeneration: number;
  isAuthenticated: boolean;
  isLoading: boolean;
  user: CurrentUser | null;
  userEmail: string | null;
  role: CurrentUser["role"] | null;
  businesses: Business[];
  isPlatformUser: boolean;
  isMerchantUser: boolean;
  refreshUser: () => Promise<CurrentUser | null>;
  login: (email: string, password: string) => Promise<CurrentUser | MfaPendingResponse>;
  signupOwner: (payload: OwnerSignupPayload) => Promise<CurrentUser | MfaPendingResponse>;
  loginWithSocial: (provider: SocialProvider, idToken: string) => Promise<CurrentUser | MfaPendingResponse>;
  completeMfaSession: () => Promise<CurrentUser>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { t } = useI18n();
  const { unavailable } = useConnectionNoticeState();
  const [isAuthenticated, setAuthenticated] = useState(false);
  const [isLoading, setLoading] = useState(true);
  const [user, setUser] = useState<CurrentUser | null>(null);
  const mountedRef = useRef(false);
  const sessionRestoreStartedRef = useRef(false);
  const [recoveryError, setRecoveryError] = useState<unknown>(null);
  const [isRecovering, setRecovering] = useState(false);
  const restoring = useRef<Promise<void> | null>(null);
  const recoveryAttempts = useRef(0);
  const [logoutError, setLogoutError] = useState(false);
  const [isLoggingOut, setLoggingOut] = useState(false);
  const logoutPending = useRef(false);
  const sessionGeneration = tokenStorage.getGeneration();
  const logout = useCallback(() => {
    if (logoutPending.current) return;
    logoutPending.current = true;
    const generation = tokenStorage.getGeneration();
    setLoggingOut(true);
    setLogoutError(false);
    void apiLogout().then(() => {
      if (!mountedRef.current) return;
      setAuthenticated(false);
      setUser(null);
      setLoading(false);
      setRecoveryError(null);
      recoveryAttempts.current = 0;
    }).catch(error => {
      if (mountedRef.current && generation === tokenStorage.getGeneration() && !axios.isCancel(error)) setLogoutError(true);
    }).finally(() => {
      logoutPending.current = false;
      if (mountedRef.current) setLoggingOut(false);
    });
  }, []);
  const acceptUser = useCallback((currentUser: CurrentUser, generation: number) => {
    assertCurrentSession(generation);
    if (!mountedRef.current) throw new Error("Authentication provider unmounted");
    setUser(currentUser);
    setAuthenticated(true);
    setRecoveryError(null);
    recoveryAttempts.current = 0;
    tokenStorage.setEmail(currentUser.email);
    tokenStorage.setUserId(currentUser.id);
    return currentUser;
  }, []);
  const loadCurrentUser = useCallback(async () => {
    const generation = tokenStorage.getGeneration();
    return acceptUser(await getCurrentUser(), generation);
  }, [acceptUser]);

  const restoreCurrentSession = useCallback(() => {
    if (restoring.current) return restoring.current;
    const generation = tokenStorage.getGeneration();
    const hadPreviousSession = Boolean(tokenStorage.getEmail());
    setRecovering(true);
    const promise = (async () => {
      try {
        await restoreSession();
        const currentUser = await getCurrentUser();
        acceptUser(currentUser, generation);
        setRecoveryError(null);
        recoveryAttempts.current = 0;
      } catch (error) {
        if (!mountedRef.current || generation !== tokenStorage.getGeneration() || axios.isCancel(error)) return;
        if (isSessionExpiryResponse(error)) {
          if (hadPreviousSession) expireBrowserSession();
          setRecoveryError(null);
        } else {
          recoveryAttempts.current += 1;
          setRecoveryError(error);
        }
      } finally {
        if (mountedRef.current && generation === tokenStorage.getGeneration()) setLoading(false);
        if (mountedRef.current) setRecovering(false);
        restoring.current = null;
      }
    })();
    restoring.current = promise;
    return promise;
  }, [acceptUser]);

  useBrowserSessionActivity(isAuthenticated, () => setRecoveryError(null));

  useEffect(() => {
    mountedRef.current = true;

    function handleAuthExpired() {
      if (!mountedRef.current) return;
      setLogoutError(false);
      setUser(null);
      setAuthenticated(false);
      setLoading(false);
      setRecoveryError(null);
    }

    function handleRecovery(event: Event) {
      if (mountedRef.current) setRecoveryError((event as CustomEvent<unknown>).detail);
    }

    window.addEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired);
    window.addEventListener(AUTH_RECOVERY_EVENT, handleRecovery);

    return () => {
      mountedRef.current = false;
      window.removeEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired);
      window.removeEventListener(AUTH_RECOVERY_EVENT, handleRecovery);
    };
  }, []);

  useEffect(() => {
    if (sessionRestoreStartedRef.current) return;
    sessionRestoreStartedRef.current = true;

    void restoreCurrentSession();
  }, [restoreCurrentSession]);

  useEffect(() => {
    if (!recoveryError) return;
    const retryAfter = (normalizeAppError(recoveryError).retryAfterSeconds || 0) * 1000;
    const retryAt = Date.now() + retryAfter;
    const recover = () => {
      if (Date.now() >= retryAt && navigator.onLine && document.visibilityState === "visible") void restoreCurrentSession();
    };
    const delay = Math.max(Math.min(60_000, 5_000 * 2 ** Math.min(recoveryAttempts.current, 4)), retryAfter);
    // A hidden/offline tick must not consume the only scheduled attempt.
    const timer = window.setInterval(recover, delay);
    window.addEventListener("online", recover);
    window.addEventListener("focus", recover);
    window.addEventListener(SERVICE_AVAILABLE_EVENT, recover);
    document.addEventListener("visibilitychange", recover);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("online", recover);
      window.removeEventListener("focus", recover);
      window.removeEventListener(SERVICE_AVAILABLE_EVENT, recover);
      document.removeEventListener("visibilitychange", recover);
    };
  }, [recoveryError, restoreCurrentSession]);

  const value = useMemo<AuthContextValue>(
    () => ({
      sessionGeneration,
      isAuthenticated,
      isLoading,
      user,
      userEmail: user?.email ?? tokenStorage.getEmail(),
      role: user?.role ?? null,
      businesses: user?.businesses ?? [],
      isPlatformUser: Boolean(user?.is_platform_user),
      isMerchantUser: Boolean(user?.is_merchant_user),
      refreshUser: async () => {
        const generation = tokenStorage.getGeneration();
        if (!tokenStorage.getAccess()) {
          const hadPreviousSession = Boolean(tokenStorage.getEmail());
          try {
            await restoreSession();
          } catch (error) {
            if (generation !== tokenStorage.getGeneration()) return null;
            if (hadPreviousSession && isSessionExpiryResponse(error)) {
              expireBrowserSession();
            }
            return null;
          }
        }
        const currentUser = await getCurrentUser();
        return acceptUser(currentUser, generation);
      },
      login: async (email: string, password: string) => {
        const response = await apiLogin({ email, password });
        if (isMfaPendingResponse(response)) return response;
        return loadCurrentUser();
      },
      signupOwner: async (payload: OwnerSignupPayload) => {
        const response = await apiSignupOwner(payload);
        if (isMfaPendingResponse(response)) return response;
        return loadCurrentUser();
      },
      loginWithSocial: async (provider: SocialProvider, idToken: string) => {
        const response = await apiSocialLogin({ provider, idToken });
        if (isMfaPendingResponse(response)) return response;
        return loadCurrentUser();
      },
      completeMfaSession: async () => {
        return loadCurrentUser();
      },
      logout,
    }),
    [acceptUser, isAuthenticated, isLoading, loadCurrentUser, logout, sessionGeneration, user],
  );

  const recoveryAppError = useMemo(() => recoveryError ? normalizeAppError(recoveryError) : undefined, [recoveryError]);
  const recoveryDelay = useRecoveryDelay(recoveryAppError);
  const connectionRelated = recoveryAppError && ["offline", "temporary", "provider"].includes(recoveryAppError.category);
  const message = recoveryAppError ? t(connectionRelated ? "auth.sessionRecoveryFailed" : recoveryAppError.messageKey) : "";
  const retry = <Button type="button" disabled={recoveryDelay > 0} isLoading={isRecovering} onClick={() => void restoreCurrentSession()}>{recoveryDelay > 0 ? t("fallback.retryAfter", { seconds: recoveryDelay }) : t("common.retry")}</Button>;
  return <AuthContext.Provider value={value}>
    {recoveryError && !isAuthenticated ? <div data-testid="session-recovery" className="mx-auto max-w-xl p-6"><ErrorState error={recoveryError} action={retry} /></div> : children}
    <NotificationPortal group="session">
    <NotificationPresence>{(logoutError || isLoggingOut) ? <div data-testid="logout-status">
      <StatusNotice tone={logoutError ? "danger" : "info"} title={t(logoutError ? "auth.logoutFailed" : "auth.loggingOut")}
        action={logoutError ? <Button type="button" onClick={logout}>{t("common.retry")}</Button> : undefined} />
    </div> : null}</NotificationPresence>
    <NotificationPresence>{recoveryError && isAuthenticated && !logoutError && !isLoggingOut && !(unavailable && connectionRelated) ? <div data-testid="session-recovery">
      <StatusNotice tone="warning" title={message} action={retry} details={recoveryAppError ? <RecoveryDetails error={recoveryAppError} /> : undefined} />
    </div> : null}</NotificationPresence>
    </NotificationPortal>
  </AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}

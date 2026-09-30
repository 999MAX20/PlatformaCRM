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
  expireBrowserSession,
  isSessionExpiryResponse,
} from "../../api/client";
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
  const [isAuthenticated, setAuthenticated] = useState(false);
  const [isLoading, setLoading] = useState(true);
  const [user, setUser] = useState<CurrentUser | null>(null);
  const mountedRef = useRef(false);
  const sessionRestoreStartedRef = useRef(false);
  const sessionGeneration = tokenStorage.getGeneration();
  const acceptUser = useCallback((currentUser: CurrentUser, generation: number) => {
    assertCurrentSession(generation);
    if (!mountedRef.current) throw new Error("Authentication provider unmounted");
    setUser(currentUser);
    setAuthenticated(true);
    tokenStorage.setEmail(currentUser.email);
    tokenStorage.setUserId(currentUser.id);
    return currentUser;
  }, []);
  const loadCurrentUser = useCallback(async () => {
    const generation = tokenStorage.getGeneration();
    return acceptUser(await getCurrentUser(), generation);
  }, [acceptUser]);

  useEffect(() => {
    mountedRef.current = true;

    function handleAuthExpired() {
      if (!mountedRef.current) return;
      setUser(null);
      setAuthenticated(false);
      setLoading(false);
    }

    window.addEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired);

    return () => {
      mountedRef.current = false;
      window.removeEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired);
    };
  }, []);

  useEffect(() => {
    if (sessionRestoreStartedRef.current) return;
    sessionRestoreStartedRef.current = true;

    async function loadUser() {
      const generation = tokenStorage.getGeneration();
      if (!tokenStorage.getAccess()) {
        const hadPreviousSession = Boolean(tokenStorage.getEmail());
        try {
          await restoreSession();
        } catch (error) {
          if (generation !== tokenStorage.getGeneration()) return;
          if (hadPreviousSession && isSessionExpiryResponse(error)) {
            expireBrowserSession();
          }
          if (mountedRef.current) setLoading(false);
          return;
        }
      }

      try {
        const currentUser = await getCurrentUser();
        if (!mountedRef.current) return;
        acceptUser(currentUser, generation);
      } catch {
        if (!mountedRef.current || generation !== tokenStorage.getGeneration()) return;
        apiLogout();
        setUser(null);
        setAuthenticated(false);
        setLoading(false);
      } finally {
        if (mountedRef.current && generation === tokenStorage.getGeneration()) setLoading(false);
      }
    }

    loadUser();
  }, [acceptUser]);

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
      logout: () => {
        apiLogout();
        setAuthenticated(false);
        setUser(null);
        setLoading(false);
      },
    }),
    [acceptUser, isAuthenticated, isLoading, loadCurrentUser, sessionGeneration, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}

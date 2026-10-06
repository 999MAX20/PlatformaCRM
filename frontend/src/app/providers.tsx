import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import axios from "axios";
import { useEffect, useRef, useState } from "react";

import { ActionConfirmProvider } from "../components/actions/ActionConfirmProvider";
import { ConnectivityStatus } from "../components/ui/ConnectivityStatus";
import { UndoToastProvider } from "../components/actions/UndoToastProvider";
import { NotificationProvider } from "../components/notifications/NotificationProvider";
import { AuthProvider, useAuth } from "../features/auth/AuthProvider";
import { I18nProvider } from "../lib/i18n";

function SessionProviders({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5 * 60_000,
            gcTime: 30 * 60_000,
            refetchOnWindowFocus: false,
            refetchOnReconnect: true,
            retry: (failureCount, error) => {
              if (axios.isCancel(error)) return false;
              if (axios.isAxiosError(error) && error.response?.status && error.response.status < 500) {
                return false;
              }
              return failureCount < 1;
            },
          },
        },
      }),
  );
  const mounted = useRef(false);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      // StrictMode replays effects without discarding this client. Only clear
      // on an actual scope change/unmount, not that development-only replay.
      queueMicrotask(() => {
        if (mounted.current) return;
        void queryClient.cancelQueries();
        queryClient.clear();
      });
    };
  }, [queryClient]);

  return (
    <QueryClientProvider client={queryClient}>
        <ConnectivityStatus />
        <ActionConfirmProvider>
          <NotificationProvider>
            <UndoToastProvider>
              {children}
            </UndoToastProvider>
          </NotificationProvider>
        </ActionConfirmProvider>
    </QueryClientProvider>
  );
}

function AuthenticatedProviders({ children }: { children: React.ReactNode }) {
  const { user, sessionGeneration } = useAuth();
  // Scope generic query keys and pending action callbacks to identity/access.
  // Profile/preferences changes deliberately preserve the current workspace.
  const scope = JSON.stringify([
    sessionGeneration, user?.id, user?.role,
    user?.is_platform_user, user?.is_merchant_user,
    user?.businesses.map((business) => business.id),
    user?.memberships, user?.effective_permissions, user?.capabilities,
  ]);
  return <SessionProviders key={scope}>{children}</SessionProviders>;
}

export function AppProviders({ children }: { children: React.ReactNode }) {
  return (
    <I18nProvider>
      <AuthProvider>
        <AuthenticatedProviders>{children}</AuthenticatedProviders>
      </AuthProvider>
    </I18nProvider>
  );
}

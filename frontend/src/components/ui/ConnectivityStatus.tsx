import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";

import { normalizeAppError, type AppError } from "../../api/appError";
import { checkServiceConnection, SERVICE_AVAILABLE_EVENT } from "../../api/connectivity";
import { ConnectivityBanner } from "./ConnectivityBanner";

const offlineError: AppError = {
  category: "offline", code: "network_unavailable", fieldErrors: {},
  messageKey: "actions.errorNetwork", retryable: true,
  retryPolicy: "user_initiated_only", source: "network",
};
type ConnectionState = "online" | "offline" | "checking" | "unavailable";

export function ConnectivityStatus({ monitor = false }: { monitor?: boolean }) {
  const queryClient = useQueryClient();
  const [state, setState] = useState<ConnectionState>(() => navigator.onLine ? "online" : "offline");
  const [error, setError] = useState(offlineError);
  const request = useRef<AbortController | null>(null);
  const currentState = useRef(state);
  currentState.current = state;

  const reconnect = useCallback(async (background = false) => {
    request.current?.abort();
    if (!navigator.onLine) { setState("offline"); setError(offlineError); return; }
    const controller = new AbortController();
    request.current = controller;
    const wasOnline = currentState.current === "online";
    if (!background || !wasOnline) setState("checking");
    try {
      await checkServiceConnection(controller.signal);
      if (controller.signal.aborted) return;
      setState("online");
      if (!wasOnline) window.dispatchEvent(new Event(SERVICE_AVAILABLE_EVENT));
      // Reads only. Never replay pending mutations after a connection failure.
      if (!wasOnline) void queryClient.refetchQueries({ type: "active" }, { cancelRefetch: false });
    } catch (cause) {
      if (controller.signal.aborted) return;
      setError({ ...normalizeAppError(cause), messageKey: "fallback.connectivity.unavailableText", retryable: true });
      setState("unavailable");
    } finally {
      if (request.current === controller) request.current = null;
    }
  }, [queryClient]);

  useEffect(() => {
    if (!monitor) return;
    const check = () => { if (document.visibilityState === "visible") void reconnect(true); };
    check();
    const interval = window.setInterval(check, 30_000);
    document.addEventListener("visibilitychange", check);
    return () => { window.clearInterval(interval); document.removeEventListener("visibilitychange", check); };
  }, [monitor, reconnect]);

  useEffect(() => {
    const offline = () => {
      request.current?.abort();
      setError(offlineError);
      setState("offline");
    };
    const online = () => { void reconnect(); };
    window.addEventListener("offline", offline);
    window.addEventListener("online", online);
    return () => {
      request.current?.abort();
      window.removeEventListener("offline", offline);
      window.removeEventListener("online", online);
    };
  }, [reconnect]);

  if (state === "online") return null;
  return <ConnectivityBanner error={error} isReconnecting={state === "checking"}
    onRetry={state === "unavailable" ? () => reconnect() : undefined} />;
}

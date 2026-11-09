import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";

import { normalizeAppError, type AppError } from "../../api/appError";
import { checkServiceConnection, SERVICE_AVAILABLE_EVENT } from "../../api/connectivity";
import { ConnectivityBanner } from "./ConnectivityBanner";
import { NotificationPortal, NotificationPresence, restoreNoticeFocus, useConnectionNoticeState } from "../notifications/NotificationHost";

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
  const [stableState, setStableState] = useState(state);
  const { setUnavailable } = useConnectionNoticeState();
  useLayoutEffect(() => {
    setUnavailable(stableState === "offline" || stableState === "unavailable");
  }, [stableState, setUnavailable]);
  const [dismissed, setDismissed] = useState<ConnectionState | null>(null);
  const card = useRef<HTMLDivElement>(null);
  const opener = useRef<HTMLElement | null>(null);
  const request = useRef<AbortController | null>(null);
  const currentState = useRef(state);
  currentState.current = state;
  const setConnection = useCallback((next: ConnectionState) => {
    currentState.current = next;
    setState(next);
    if (next !== "checking") setStableState(next);
  }, []);
  useEffect(() => {
    setDismissed(null);
  }, [stableState]);

  const reconnect = useCallback(async (background = false) => {
    request.current?.abort();
    if (!navigator.onLine) { setConnection("offline"); setError(offlineError); return; }
    const controller = new AbortController();
    request.current = controller;
    const wasOnline = currentState.current === "online";
    if (!background || !wasOnline) setConnection("checking");
    try {
      await checkServiceConnection(controller.signal);
      if (controller.signal.aborted) return;
      restoreNoticeFocus(card.current, opener.current);
      setConnection("online");
      if (!wasOnline) window.dispatchEvent(new Event(SERVICE_AVAILABLE_EVENT));
      // Reads only. Never replay pending mutations after a connection failure.
      if (!wasOnline) void queryClient.refetchQueries({ type: "active" }, { cancelRefetch: false });
    } catch (cause) {
      if (controller.signal.aborted) return;
      setError({ ...normalizeAppError(cause), messageKey: "fallback.connectivity.unavailableText", retryable: true });
      setConnection("unavailable");
    } finally {
      if (request.current === controller) request.current = null;
    }
  }, [queryClient, setConnection]);

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
      setConnection("offline");
    };
    const online = () => { void reconnect(); };
    window.addEventListener("offline", offline);
    window.addEventListener("online", online);
    return () => {
      request.current?.abort();
      window.removeEventListener("offline", offline);
      window.removeEventListener("online", online);
    };
  }, [reconnect, setConnection]);

  const visible = state !== "online" && dismissed !== stableState;
  return <NotificationPortal group="connection"><NotificationPresence>{visible ? <div ref={card}
    onFocusCapture={event => {
      if (!event.currentTarget.contains(event.relatedTarget as Node | null)) opener.current = event.relatedTarget instanceof HTMLElement ? event.relatedTarget : null;
    }}>
    <ConnectivityBanner error={error} isReconnecting={state === "checking"}
      onDismiss={() => { restoreNoticeFocus(card.current, opener.current); setDismissed(stableState); }}
      onRetry={state === "unavailable" ? () => reconnect() : undefined} />
  </div> : null}</NotificationPresence></NotificationPortal>;
}

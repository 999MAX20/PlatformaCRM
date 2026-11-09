import { handleSessionRecoveryError } from "./client";
import { assertCurrentSession, refreshToken } from "./token";
import { runAnnouncementEvents } from "./announcementEventStream";
import { tokenStorage } from "../lib/storage";
import type { Id } from "../types";

export function subscribeAnnouncementEvents(business: Id, callbacks: {
  invalidate: () => Promise<unknown>;
  forbidden: () => Promise<unknown>;
}) {
  const controller = new AbortController();
  const generation = tokenStorage.getGeneration();
  const guard = () => {
    if (generation !== tokenStorage.getGeneration()) controller.abort();
    assertCurrentSession(generation);
    if (controller.signal.aborted) throw new Error("Event subscription closed");
  };
  void runAnnouncementEvents({
    signal: controller.signal,
    connect: async signal => {
      guard();
      const access = tokenStorage.getAccess();
      if (!access) { controller.abort(); throw new Error("No active session"); }
      // SSE has its own same-origin proxy route, independent of the REST base URL.
      const response = await fetch(`/api/notifications/events/?business=${encodeURIComponent(business)}`, {
        headers: { Authorization: `Bearer ${access}`, Accept: "text/event-stream" },
        credentials: "omit", cache: "no-store", signal,
      });
      guard();
      return response;
    },
    reauthenticate: async () => {
      guard();
      try { await refreshToken(); guard(); }
      catch (error) {
        if (!controller.signal.aborted && generation === tokenStorage.getGeneration()) handleSessionRecoveryError(error);
        controller.abort();
        throw error;
      }
    },
    invalidate: async () => { guard(); await callbacks.invalidate(); },
    forbidden: async () => { guard(); await callbacks.forbidden(); },
  }).catch(() => { /* Session change/unmount ends the old subscription. */ });
  return () => controller.abort();
}

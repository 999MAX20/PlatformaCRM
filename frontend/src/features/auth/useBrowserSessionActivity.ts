import { useEffect, useRef } from "react";

import { recordSessionActivity } from "../../api/auth";
import { handleSessionRecoveryError } from "../../api/client";
import { tokenStorage } from "../../lib/storage";

export function useBrowserSessionActivity(authenticated: boolean, onRecovered: () => void) {
  const recovered = useRef(onRecovered);
  recovered.current = onRecovered;
  useEffect(() => {
    if (!authenticated) return;
    // Login/foreground restoration already records activity. Avoid a redundant
    // rotation immediately before the user navigates away from the login page.
    let lastActivity = Date.now();
    let pending = false;
    const generation = tokenStorage.getGeneration();
    async function activity(force = false) {
      if (document.visibilityState !== "visible" || !navigator.onLine || pending) return;
      if (!force && Date.now() - lastActivity < 60_000) return;
      if (generation !== tokenStorage.getGeneration()) return;
      lastActivity = Date.now();
      pending = true;
      try {
        await recordSessionActivity();
        if (generation !== tokenStorage.getGeneration()) return;
        lastActivity = Date.now();
        recovered.current();
      } catch (error) {
        if (generation === tokenStorage.getGeneration()) handleSessionRecoveryError(error);
      } finally { pending = false; }
    }
    const interact = (event: Event) => { if (event.isTrusted) void activity(); };
    const resume = () => { void activity(true); };
    for (const name of ["pointerdown", "keydown", "wheel", "touchstart"]) {
      window.addEventListener(name, interact, { passive: true });
    }
    document.addEventListener("visibilitychange", resume);
    window.addEventListener("focus", resume);
    window.addEventListener("online", resume);
    return () => {
      for (const name of ["pointerdown", "keydown", "wheel", "touchstart"]) window.removeEventListener(name, interact);
      document.removeEventListener("visibilitychange", resume);
      window.removeEventListener("focus", resume);
      window.removeEventListener("online", resume);
    };
  }, [authenticated]);
}

import { useEffect, useRef, useState } from "react";
import { startGoogleFlow } from "../../api/token";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { useI18n } from "../../lib/i18n";

let scriptRequest: Promise<void> | undefined;
function loadGoogle() {
  if (window.google?.accounts?.id) return Promise.resolve();
  if (scriptRequest) return scriptRequest;
  scriptRequest = new Promise<void>((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    const timer = window.setTimeout(() => fail(), 15_000);
    function fail() {
      window.clearTimeout(timer);
      script.remove();
      scriptRequest = undefined;
      reject(new Error("Google Identity Services unavailable"));
    }
    script.onerror = fail;
    script.onload = () => {
      window.clearTimeout(timer);
      if (window.google?.accounts?.id) resolve();
      else fail();
    };
    document.head.appendChild(script);
  });
  return scriptRequest;
}

export function GoogleSignInButton({ disabled, onCredential, text = "continue_with" }: {
  disabled: boolean;
  onCredential: (credential: string) => Promise<boolean>;
  text?: "continue_with" | "signup_with";
}) {
  const { t, language } = useI18n();
  const container = useRef<HTMLDivElement>(null);
  const callback = useRef(onCredential);
  const blocked = useRef(disabled);
  callback.current = onCredential;
  blocked.current = disabled;
  const [attempt, setAttempt] = useState(0);
  const [ready, setReady] = useState(false);
  const [hasButton, setHasButton] = useState(false);
  const [error, setError] = useState<string>();

  useEffect(() => {
    let active = true;
    let submitted = false;
    let refreshing = false;
    let generation = 0;
    let expiresAt = 0;
    let draw: ((restoreFocus?: boolean) => void) | undefined;
    let expiry: number | undefined;
    setReady(false);
    setHasButton(false);
    setError(undefined);
    const mount = container.current;
    mount?.replaceChildren();
    async function prepare() {
      if (!active || submitted || refreshing) return;
      refreshing = true;
      const restoreFocus = mount?.contains(document.activeElement);
      setReady(false);
      const currentGeneration = ++generation;
      try {
        await loadGoogle();
        if (!active) return;
        const flow = await startGoogleFlow();
        if (!active || !mount) return;
        const identity = window.google!.accounts!.id!;
        identity.initialize({
          client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID!, nonce: flow.nonce, auto_select: false,
          callback: response => {
            if (!active || refreshing || currentGeneration !== generation || blocked.current || submitted) return;
            if (!response.credential) { setError(t("auth.socialFailed")); return; }
            submitted = true;
            window.clearTimeout(expiry);
            blocked.current = true;
            void callback.current(response.credential).then(completed => {
              if (active && !completed) setAttempt(value => value + 1);
            });
          },
        });
        let lastWidth = 0;
        draw = (restore = false) => {
          const width = Math.min(400, Math.floor(mount.getBoundingClientRect().width));
          if (!active || width <= 0 || width === lastWidth) return;
          lastWidth = width;
          restore ||= mount.contains(document.activeElement);
          mount.replaceChildren();
          identity.renderButton(mount, {
            type: "standard", theme: "outline", size: "medium", text, width, locale: language,
          });
          if (restore) window.requestAnimationFrame(() => {
            if (active && document.activeElement === document.body) {
              mount.querySelector<HTMLElement>('iframe, button, [role="button"]')?.focus();
            }
          });
        };
        draw(restoreFocus);
        setHasButton(true);
        setReady(true);
        expiresAt = Date.now() + flow.expires_in * 1000;
        expiry = window.setTimeout(() => {
          if (document.visibilityState === "visible") void prepare();
        }, Math.max(1000, flow.expires_in * 1000));
      } catch (err) {
        expiresAt = 0;
        if (active) setError(err instanceof Error && err.message === "Google Identity Services unavailable" ? t("auth.socialFailed") : getApiErrorMessage(err));
      } finally {
        refreshing = false;
      }
    }
    const resume = () => {
      if (document.visibilityState === "visible" && expiresAt && Date.now() >= expiresAt) {
        window.clearTimeout(expiry);
        void prepare();
      }
    };
    const resize = new ResizeObserver(() => {
      if (!refreshing && !submitted) draw?.();
    });
    if (mount) resize.observe(mount);
    void prepare();
    document.addEventListener("visibilitychange", resume);
    window.addEventListener("focus", resume);
    return () => {
      active = false;
      window.clearTimeout(expiry);
      document.removeEventListener("visibilitychange", resume);
      window.removeEventListener("focus", resume);
      resize.disconnect();
      mount?.replaceChildren();
    };
  }, [attempt, language, t, text]);

  return <div className="col-span-full w-full min-w-0" aria-busy={!ready && !error}>
    <div className="relative min-h-11">
      <div ref={container} inert={disabled || !ready} className={`flex min-h-11 items-center${disabled ? " pointer-events-none opacity-60" : ""}`} />
      {!hasButton && !ready && !error ? <p role="status" className="pointer-events-none absolute inset-0 flex items-center text-sm text-platforma-subtle">{t("googleAuth.loading")}</p> : null}
    </div>
    {error ? <div className="space-y-2"><p role="alert" className="text-sm text-platforma-danger">{error}</p>
      <Button type="button" variant="secondary" disabled={disabled} onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button>
    </div> : null}
  </div>;
}

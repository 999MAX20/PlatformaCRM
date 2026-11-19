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

export function GoogleSignInButton({ disabled, onCredential }: {
  disabled: boolean;
  onCredential: (credential: string) => Promise<boolean>;
}) {
  const { t, language } = useI18n();
  const container = useRef<HTMLDivElement>(null);
  const callback = useRef(onCredential);
  const blocked = useRef(disabled);
  callback.current = onCredential;
  blocked.current = disabled;
  const [attempt, setAttempt] = useState(0);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string>();

  useEffect(() => {
    let active = true;
    let submitted = false;
    let expiry: number | undefined;
    setReady(false);
    setError(undefined);
    const mount = container.current;
    mount?.replaceChildren();
    void (async () => {
      await loadGoogle();
      if (!active) return;
      const flow = await startGoogleFlow();
      if (!active || !mount) return;
      const identity = window.google!.accounts!.id!;
      identity.initialize({
        client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID!, nonce: flow.nonce, auto_select: false,
        callback: response => {
          if (!active || blocked.current || submitted) return;
          if (!response.credential) { setError(t("auth.socialFailed")); return; }
          submitted = true;
          blocked.current = true;
          void callback.current(response.credential).then(completed => {
            if (active && !completed) setAttempt(value => value + 1);
          });
        },
      });
      identity.renderButton(mount, {
        type: "standard", theme: "outline", size: "large", text: "continue_with",
        width: Math.min(400, Math.floor(mount.getBoundingClientRect().width)), locale: language,
      });
      setReady(true);
      expiry = window.setTimeout(() => {
        mount.replaceChildren(); setReady(false); setError(t("googleAuth.expired"));
      }, flow.expires_in * 1000);
    })().catch(err => {
      if (active) setError(err instanceof Error && err.message === "Google Identity Services unavailable" ? t("auth.socialFailed") : getApiErrorMessage(err));
    });
    return () => { active = false; window.clearTimeout(expiry); mount?.replaceChildren(); };
  }, [attempt, language, t]);

  return <div className="col-span-full w-full min-w-0" aria-busy={!ready && !error}>
    <div ref={container} inert={disabled} className={disabled ? "pointer-events-none opacity-60" : undefined} />
    {!ready && !error ? <p role="status" className="text-sm text-platforma-subtle">{t("googleAuth.loading")}</p> : null}
    {error ? <div className="space-y-2"><p role="alert" className="text-sm text-platforma-danger">{error}</p>
      <Button type="button" variant="secondary" disabled={disabled} onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button>
    </div> : null}
  </div>;
}

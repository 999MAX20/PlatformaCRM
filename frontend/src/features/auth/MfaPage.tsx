import { ArrowRight } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router";

import {
  confirmMfaEnrollment,
  isMfaPendingResponse,
  startMfaEnrollment,
  verifyMfaLogin,
  type MfaEnrollment,
  type MfaPendingResponse,
} from "../../api/auth";
import { consumeSessionExpiredReturnTo, getApiErrorMessage } from "../../api/client";
import { LanguageSelector } from "../../components/layout/LanguageSelector";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { StatusNotice } from "../../components/ui/StatusNotice";
import { useI18n } from "../../lib/i18n";
import { useAuth } from "./AuthProvider";
import { AuthenticatorEnrollment } from "./AuthenticatorEnrollment";
import { MfaCodeInput } from "./MfaCodeInput";
import { getAuthReturnPathFromState, getPostAuthReturnPath } from "./authReturnPath";
import "./authLoginSerenity.css";

function readPending(): MfaPendingResponse | null {
  try {
    const value = JSON.parse(sessionStorage.getItem("zani_mfa_pending") || "null");
    return isMfaPendingResponse(value) ? value : null;
  } catch {
    return null;
  }
}

export function MfaPage({ embedded = false, onComplete }: { embedded?: boolean; onComplete?: () => Promise<void> } = {}) {
  const { t } = useI18n();
  const navigate = useNavigate();
  const location = useLocation();
  const { completeMfaSession } = useAuth();
  const pending = useMemo(readPending, []);
  const [enrollment, setEnrollment] = useState<MfaEnrollment | null>(null);
  const [code, setCode] = useState("");
  const [recoveryMode, setRecoveryMode] = useState(false);
  const [verified, setVerified] = useState(false);
  const [enrollmentAttempt, setEnrollmentAttempt] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const submitting = useRef(false);

  useEffect(() => {
    if (!pending || pending.code !== "mfa_enrollment_required") return;
    let active = true;
    setError(null);
    setLoading(true);
    startMfaEnrollment(pending.challenge_token)
      .then((result) => {
        if (active) setEnrollment(result);
      })
      .catch((err) => {
        if (active) setError(getApiErrorMessage(err));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [pending, enrollmentAttempt]);

  async function finishSession() {
    const user = await completeMfaSession();
    sessionStorage.removeItem("zani_mfa_pending");
    if (onComplete) { await onComplete(); return; }
    const storedReturnTo = consumeSessionExpiredReturnTo();
    const intendedPath = getAuthReturnPathFromState(location.state) || storedReturnTo;
    navigate(getPostAuthReturnPath(user.is_platform_user, intendedPath), { replace: true });
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!pending || submitting.current) return;
    submitting.current = true;
    setError(null);
    setLoading(true);
    try {
      if (pending.code === "mfa_enrollment_required") {
        await confirmMfaEnrollment(pending.challenge_token, code);
      } else {
        await verifyMfaLogin(pending.challenge_token, code);
      }
      setVerified(true);
      setEnrollment(null);
      setCode("");
      sessionStorage.removeItem("zani_mfa_pending");
      await finishSession();
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoading(false);
      submitting.current = false;
    }
  }

  async function continueSignIn() {
    if (submitting.current) return;
    submitting.current = true;
    setError(null);
    setLoading(true);
    try {
      await finishSession();
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoading(false);
      submitting.current = false;
    }
  }

  const title = !pending ? t("mfa.sessionExpiredTitle") : t("mfa.title");
  const description = !pending ? t("mfa.sessionExpiredText") : verified ? t("mfa.completingText") : pending.code === "mfa_enrollment_required" ? t("mfa.addAuthenticator") : t("mfa.text");
  const Surface = embedded ? "div" : "main";

  return (
    <Surface className={embedded ? "space-y-4" : "serenity-login serenity-login--signal-field serenity-login--mfa"}>
      {!embedded && <><div className="serenity-login__ambient" aria-hidden="true"><span /><span /><span /><span /><span /></div>
      <header className="serenity-login__header">
        <Link className="serenity-login__brand" to="/login">
          <img className="serenity-login__brand-logo" src="/brand/platforma-crm-logo-transparent.png" alt="PlatformaCRM" width={2170} height={725} />
        </Link>
        <div className="serenity-login__header-actions">
          <LanguageSelector className="serenity-login__language" />
        </div>
      </header></>}

      <div className={embedded ? "" : "serenity-login__layout"}>
        {!embedded && <section className="serenity-login__story" aria-label={t("mfa.title")}>
          <h1>{t("mfa.hero")}</h1>
        </section>}
        <section className={embedded ? "" : "serenity-login__form-area"} aria-label={title}>
          <div className={embedded ? "space-y-4" : `serenity-login__card${!pending ? " serenity-login__card--mfa-expired" : ""}`}>
            <h2 aria-live="polite">{title}</h2>
            <p className="serenity-login__card-copy">{description}</p>

            {error ? <StatusNotice compact className="mb-3" tone="danger" title={t("fallback.inline.title")} description={error} /> : null}

            {!pending ? (
              <Link className="serenity-login__signup-link" to="/login">{t("mfa.backToLogin")}</Link>
            ) : verified ? (
              error ? <Button className="serenity-login__primary" type="button" isLoading={loading} autoFocus onClick={() => void continueSignIn()}>
                {t("common.retry")}
              </Button> : <p role="status" className="text-center text-sm text-platforma-muted">{t("common.loading")}</p>
            ) : (
              <form className="serenity-login__form" onSubmit={submit}>
                {pending.code === "mfa_enrollment_required" && enrollment ? <AuthenticatorEnrollment enrollment={enrollment} /> : null}
                {recoveryMode ? <Input
                  label={t("mfa.recoveryCodeLabel")}
                  value={code}
                  onChange={(event) => setCode(event.target.value)}
                  autoComplete="off"
                  autoFocus
                  disabled={loading}
                  required
                /> : <MfaCodeInput
                  label={t("mfa.codeLabel")}
                  value={code}
                  onChange={setCode}
                  disabled={loading || (pending.code === "mfa_enrollment_required" && !enrollment)}
                />}
                {pending.code !== "mfa_enrollment_required" ? <div className="text-center">
                  <Button type="button" variant="ghost" disabled={loading} onClick={() => {
                    setRecoveryMode(mode => !mode); setCode(""); setError(null);
                  }}>{t(recoveryMode ? "mfa.useAuthenticator" : "mfa.useRecoveryCode")}</Button>
                  {recoveryMode ? <p className="mt-1 text-xs leading-5 text-platforma-muted">{t("mfa.recoveryHint")}</p> : null}
                </div> : null}
                {error && pending.code === "mfa_enrollment_required" && !enrollment ? (
                  <Button type="button" variant="secondary" disabled={loading} onClick={() => setEnrollmentAttempt((attempt) => attempt + 1)}>{t("common.retry")}</Button>
                ) : null}
                <Button className="serenity-login__primary" type="submit" isLoading={loading} disabled={pending.code === "mfa_enrollment_required" && !enrollment}>
                  {pending.code === "mfa_enrollment_required" ? t("mfa.enable") : t("auth.submit")}
                  <ArrowRight size={18} />
                </Button>
              </form>
            )}
            {pending && !verified ? <div className="serenity-login__links"><Link to="/login">{t("mfa.backToLogin")}</Link></div> : null}
          </div>
        </section>
      </div>
    </Surface>
  );
}

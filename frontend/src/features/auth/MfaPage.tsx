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

export function MfaPage() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const location = useLocation();
  const { completeMfaSession } = useAuth();
  const pending = useMemo(readPending, []);
  const [enrollment, setEnrollment] = useState<MfaEnrollment | null>(null);
  const [code, setCode] = useState("");
  const [verified, setVerified] = useState(false);
  const [enrollmentAttempt, setEnrollmentAttempt] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const continueButton = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (verified && !loading) continueButton.current?.focus();
  }, [verified, loading]);

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
    const storedReturnTo = consumeSessionExpiredReturnTo();
    const intendedPath = getAuthReturnPathFromState(location.state) || storedReturnTo;
    navigate(getPostAuthReturnPath(user.is_platform_user, intendedPath), { replace: true });
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!pending) return;
    setError(null);
    setLoading(true);
    try {
      if (pending.code === "mfa_enrollment_required") {
        await confirmMfaEnrollment(pending.challenge_token, code);
        setVerified(true);
        setEnrollment(null);
        setCode("");
        sessionStorage.removeItem("zani_mfa_pending");
      } else {
        await verifyMfaLogin(pending.challenge_token, code);
        setVerified(true);
        setCode("");
        sessionStorage.removeItem("zani_mfa_pending");
        await finishSession();
      }
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  async function continueSignIn() {
    setError(null);
    setLoading(true);
    try {
      await finishSession();
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  const title = !pending ? t("mfa.sessionExpiredTitle") : verified ? t("mfa.confirmedTitle") : t("mfa.title");
  const description = !pending ? t("mfa.sessionExpiredText") : verified ? t("mfa.confirmedText") : pending.code === "mfa_enrollment_required" ? t("mfa.addAuthenticator") : t("mfa.text");

  return (
    <main className="serenity-login serenity-login--signal-field serenity-login--mfa">
      <div className="serenity-login__ambient" aria-hidden="true"><span /><span /><span /><span /><span /></div>
      <header className="serenity-login__header">
        <Link className="serenity-login__brand" to="/login">
          <img className="serenity-login__brand-logo" src="/brand/platforma-crm-logo-transparent.png" alt="PlatformaCRM" width={2170} height={725} />
        </Link>
        <div className="serenity-login__header-actions">
          <LanguageSelector className="serenity-login__language" />
        </div>
      </header>

      <div className="serenity-login__layout">
        <section className="serenity-login__story" aria-label={t("mfa.title")}>
          <h1>{t("mfa.hero")}</h1>
        </section>
        <section className="serenity-login__form-area" aria-label={title}>
          <div className="serenity-login__card">
            <h2 aria-live="polite">{title}</h2>
            <p className="serenity-login__card-copy">{description}</p>

            {error ? <StatusNotice compact className="mb-3" tone="danger" title={t("fallback.inline.title")} description={error} /> : null}

            {!pending ? (
              <Link className="serenity-login__signup-link" to="/login">{t("mfa.backToLogin")}</Link>
            ) : verified ? (
              <Button ref={continueButton} className="serenity-login__primary" type="button" isLoading={loading} onClick={() => void continueSignIn()}>
                {t("auth.submit")}<ArrowRight size={18} />
              </Button>
            ) : (
              <form className="serenity-login__form" onSubmit={submit}>
                {pending.code === "mfa_enrollment_required" && enrollment ? <AuthenticatorEnrollment enrollment={enrollment} /> : null}
                <div className={pending.code === "mfa_enrollment_required" ? "mx-auto w-48 max-w-full text-center" : undefined}>
                <Input
                  label={t("mfa.codeLabel")}
                  value={code}
                  onChange={(event) => setCode(event.target.value)}
                  autoComplete="one-time-code"
                  inputMode="numeric"
                  placeholder={pending.code === "mfa_enrollment_required" ? "000000" : t("mfa.codePlaceholder")}
                  pattern={pending.code === "mfa_enrollment_required" ? "[0-9]{6}" : undefined}
                  maxLength={pending.code === "mfa_enrollment_required" ? 6 : undefined}
                  className={pending.code === "mfa_enrollment_required" ? "text-center font-mono text-lg tracking-[0.25em]" : undefined}
                  disabled={loading || (pending.code === "mfa_enrollment_required" && !enrollment)}
                  required
                />
                </div>
                {pending.code !== "mfa_enrollment_required" ? <p className="text-xs font-semibold leading-5 text-platforma-faint">{t("mfa.recoveryHint")}</p> : null}
                {error && pending.code === "mfa_enrollment_required" && !enrollment ? (
                  <Button type="button" variant="secondary" disabled={loading} onClick={() => setEnrollmentAttempt((attempt) => attempt + 1)}>{t("common.retry")}</Button>
                ) : null}
                <Button className="serenity-login__primary" type="submit" isLoading={loading} disabled={pending.code === "mfa_enrollment_required" && !enrollment}>
                  {pending.code === "mfa_enrollment_required" ? t("mfa.enable") : t("auth.submit")}
                  <ArrowRight size={18} />
                </Button>
              </form>
            )}
            {pending && !verified ? <div className="serenity-login__links mt-4"><Link to="/login">{t("mfa.backToLogin")}</Link></div> : null}
          </div>
        </section>
      </div>
    </main>
  );
}

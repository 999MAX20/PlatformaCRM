import { ArrowRight, Copy, KeyRound, ShieldCheck, Zap } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
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
import { ErrorState } from "../../components/ui/StateViews";
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
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!pending || pending.code !== "mfa_enrollment_required") return;
    let active = true;
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
  }, [pending]);

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
        const result = await confirmMfaEnrollment(pending.challenge_token, code);
        setRecoveryCodes(result.recovery_codes || []);
        setCode("");
      } else {
        await verifyMfaLogin(pending.challenge_token, code);
        await finishSession();
      }
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  if (!pending) {
    return (
      <main className="serenity-login">
        <div className="serenity-login__layout">
          <section className="serenity-login__form-area">
            <div className="serenity-login__card">
              <h2>{t("mfa.sessionExpiredTitle")}</h2>
              <p className="serenity-login__card-copy">{t("mfa.sessionExpiredText")}</p>
              <Link className="serenity-login__signup-link" to="/login">{t("mfa.backToLogin")}</Link>
            </div>
          </section>
        </div>
      </main>
    );
  }

  return (
    <main className="serenity-login">
      <div className="serenity-login__ambient" aria-hidden="true"><span /><span /><span /></div>
      <header className="serenity-login__header">
        <Link className="serenity-login__brand" to="/login">
          <span className="serenity-login__brand-mark" aria-hidden="true"><Zap size={20} /></span>
          <span className="serenity-login__brand-copy"><strong>PlatformaCRM</strong><small>{t("auth.brandTagline")}</small></span>
        </Link>
        <LanguageSelector className="serenity-login__language" />
      </header>

      <div className="serenity-login__layout">
        <section className="serenity-login__story" aria-label={t("mfa.title")}>
          <h1>{t("mfa.hero")}</h1>
        </section>
        <section className="serenity-login__form-area">
          <div className="serenity-login__card">
            <div className="mb-4 flex items-center gap-3">
              <span className="grid h-11 w-11 place-items-center rounded-2xl bg-brand-50 text-brand-700"><ShieldCheck size={22} /></span>
              <div><h2>{t("mfa.title")}</h2><p className="serenity-login__card-copy">{t("mfa.text")}</p></div>
            </div>

            {error ? <div className="mb-3"><ErrorState message={error} /></div> : null}

            {recoveryCodes.length ? (
              <div className="grid gap-4">
                <StatusNotice tone="warning" title={t("mfa.recoveryWarning")} />
                <div className="grid grid-cols-2 gap-2 rounded-2xl bg-platforma-ink p-4 font-mono text-sm text-white">
                  {recoveryCodes.map((recoveryCode) => <span key={recoveryCode}>{recoveryCode}</span>)}
                </div>
                <Button type="button" variant="secondary" onClick={() => navigator.clipboard.writeText(recoveryCodes.join("\n"))}>
                  <Copy size={17} />{t("mfa.copyCodes")}
                </Button>
                <Button type="button" onClick={() => void finishSession()}>{t("mfa.continue")}<ArrowRight size={18} /></Button>
              </div>
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
                  leftIcon={pending.code === "mfa_enrollment_required" ? undefined : <KeyRound size={18} />}
                  required
                />
                </div>
                {pending.code !== "mfa_enrollment_required" ? <p className="text-xs font-semibold leading-5 text-platforma-faint">{t("mfa.recoveryHint")}</p> : null}
                <Button type="submit" isLoading={loading} disabled={pending.code === "mfa_enrollment_required" && !enrollment}>
                  {pending.code === "mfa_enrollment_required" ? t("mfa.enable") : t("mfa.verify")}
                  <ArrowRight size={18} />
                </Button>
              </form>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}

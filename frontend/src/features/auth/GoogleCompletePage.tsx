import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useLocation, useNavigate } from "react-router";
import { z } from "zod";
import { getGoogleFlow, linkGoogle, isMfaPendingResponse, type GooglePending, type GoogleSignupPayload } from "../../api/token";
import { getMfaStatus } from "../../api/auth";
import { getApiErrorMessage } from "../../api/client";
import { normalizeAppError } from "../../api/appError";
import { LanguageSelector } from "../../components/layout/LanguageSelector";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { StatusNotice } from "../../components/ui/StatusNotice";
import { useI18n } from "../../lib/i18n";
import { documentPath, legalDocuments } from "../documents/documents";
import { useAuth } from "./AuthProvider";
import { getAuthReturnPathFromState, getPostAuthReturnPath } from "./authReturnPath";
import "./authLoginSerenity.css";

export function GoogleCompletePage() {
  const { t } = useI18n();
  const auth = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [flow, setFlow] = useState<GooglePending>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();
  const [expired, setExpired] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [busy, setBusy] = useState(false);
  const [password, setPassword] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [mfaEnabled, setMfaEnabled] = useState<boolean>();
  const [linked, setLinked] = useState(false);
  const schema = z.object({
    full_name: z.string().trim().min(2, t("validation.name")).max(255),
    phone: z.string().trim().min(5, t("validation.phone")).max(32),
    business_name: z.string().trim().min(2, t("validation.businessName")).max(255),
    business_type: z.string().min(1),
    city: z.string().trim().max(128),
    accepted_documents: z.array(z.string()).refine(values => legalDocuments.every(doc => values.includes(doc.id)), t("documents.required")),
  });
  const { register, handleSubmit, setValue, watch, formState: { errors, isSubmitting } } = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema), defaultValues: { business_type: "other", city: "", accepted_documents: [] },
  });

  useEffect(() => {
    let active = true;
    let timer: number | undefined;
    setLoading(true); setError(undefined); setExpired(false);
    void getGoogleFlow().then(result => {
      if (!active) return;
      setFlow(result);
      setValue("full_name", result.full_name);
      timer = window.setTimeout(() => setExpired(true), result.expires_in * 1000);
    }).catch(err => {
      if (!active) return;
      setError(getApiErrorMessage(err));
      if (normalizeAppError(err).code === "google_flow_invalid") setExpired(true);
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; window.clearTimeout(timer); };
  }, [attempt, setValue]);

  useEffect(() => {
    if (!auth.isAuthenticated || flow?.code !== "google_link_required") return;
    let active = true;
    void getMfaStatus().then(status => { if (active) setMfaEnabled(status.enabled); })
      .catch(err => { if (active) setError(getApiErrorMessage(err)); });
    return () => { active = false; };
  }, [auth.isAuthenticated, auth.user?.id, flow, attempt]);

  function onFailure(err: unknown) {
    setError(getApiErrorMessage(err));
    if (normalizeAppError(err).code === "google_flow_invalid") setExpired(true);
  }

  async function onSignup(values: GoogleSignupPayload) {
    setError(undefined);
    try {
      const result = await auth.signupWithGoogle(values);
      if (isMfaPendingResponse(result)) {
        sessionStorage.setItem("zani_mfa_pending", JSON.stringify(result));
        navigate("/mfa", { replace: true, state: location.state });
      } else navigate(getPostAuthReturnPath(result.is_platform_user, getAuthReturnPathFromState(location.state)), { replace: true });
    } catch (err) { onFailure(err); }
  }

  async function onLink(event: React.FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true); setError(undefined);
    try {
      await linkGoogle({ password, mfa_code: mfaEnabled ? mfaCode : undefined });
      setPassword(""); setMfaCode(""); setLinked(true);
    } catch (err) { onFailure(err); }
    finally { setBusy(false); }
  }

  const sameAccount = auth.user?.email.toLowerCase() === flow?.email.toLowerCase();
  const signup = flow?.code === "google_signup_required";
  const title = linked ? t("googleAuth.linked") : signup ? t("googleAuth.signupTitle") : t("googleAuth.linkTitle");
  return <main className="serenity-login serenity-login--signal-field serenity-login--password-reset">
    <div className="serenity-login__ambient" aria-hidden="true"><span /><span /><span /><span /><span /></div>
    <section className="glass-panel w-full max-w-lg rounded-[2rem] p-6 sm:p-8" aria-busy={loading || auth.isLoading}>
      <div className="mb-6 flex items-center justify-between gap-4">
        <Link to="/login" className="platforma-focus-ring rounded-control"><img src="/brand/platforma-crm-logo-transparent.png" width={160} height={54} alt="PlatformaCRM" /></Link>
        <LanguageSelector />
      </div>
      <h1 className="mb-4 text-2xl font-semibold tracking-tight text-midnight">{title}</h1>
      {loading || auth.isLoading ? <p role="status">{t("common.loadingData")}</p> : linked ? <>
        <StatusNotice tone="success" title={t("googleAuth.linkedText")} />
        <Link className="platforma-focus-ring mt-5 block rounded-control font-semibold text-brand-700 underline" to={getPostAuthReturnPath(auth.isPlatformUser)}>{t("googleAuth.continue")}</Link>
      </> : <>
        {error && !expired ? <StatusNotice className="mb-4" tone="danger" title={error} /> : null}
        {expired ? <StatusNotice tone="warning" title={t("googleAuth.expired")} /> : !flow ? <Button onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button> : <>
          <p className="mb-5 break-words text-sm text-platforma-subtle">{flow.email}</p>
          {signup ? auth.isAuthenticated ? <StatusNotice tone="warning" title={t("googleAuth.wrongAccount")} /> : <form className="space-y-4" onSubmit={handleSubmit(onSignup)} noValidate>
            <p className="text-sm leading-6 text-platforma-subtle">{t("googleAuth.signupText")}</p>
            <Input label={t("signup.yourName")} autoComplete="name" error={errors.full_name?.message} {...register("full_name")} />
            <Input label={t("signup.phone")} type="tel" autoComplete="tel" error={errors.phone?.message} {...register("phone")} />
            <Input label={t("signup.businessName")} autoComplete="organization" error={errors.business_name?.message} {...register("business_name")} />
            <Select label={t("signup.businessType")} options={["beauty", "medical", "dentistry", "education", "autoservice", "sauna", "other"].map(value => ({ value, label: t(`businessType.${value}`) }))} value={watch("business_type")} {...register("business_type")} />
            <Input label={t("googleAuth.city")} autoComplete="address-level2" error={errors.city?.message} {...register("city")} />
            <fieldset className="space-y-3">
              <legend className="mb-3 text-sm font-semibold">{t("documents.title")}</legend>
              {legalDocuments.map(doc => <div key={doc.id} className="flex items-start gap-3 text-sm leading-5">
                <input id={`google-accept-${doc.id}`} type="checkbox" value={doc.id} {...register("accepted_documents")} className="platforma-focus-ring mt-0.5 h-4 w-4 shrink-0 accent-brand-600" aria-describedby={errors.accepted_documents ? "google-documents-error" : undefined} />
                <label htmlFor={`google-accept-${doc.id}`}>{t(doc.id === "privacy" ? "documents.read" : "documents.accept")} {" "}
                  <Link to={documentPath(doc.id)} target="_blank" rel="noopener noreferrer" className="platforma-focus-ring rounded-sm underline underline-offset-4">{t(doc.titleKey)}</Link>
                </label>
              </div>)}
              {errors.accepted_documents ? <p id="google-documents-error" role="alert" className="text-sm text-platforma-danger">{errors.accepted_documents.message}</p> : null}
            </fieldset>
            <Button type="submit" className="w-full" isLoading={isSubmitting}>{t("signup.freeSubmit")}</Button>
          </form> : !auth.isAuthenticated ? <div className="space-y-4">
            <p className="text-sm leading-6 text-platforma-subtle">{t("googleAuth.loginFirst")}</p>
            <Link className="platforma-focus-ring block rounded-control font-semibold text-brand-700 underline" to="/login" state={{ email: flow.email, from: { pathname: "/google/complete" } }}>{t("auth.submit")}</Link>
          </div> : !sameAccount ? <>
            <StatusNotice tone="warning" title={t("googleAuth.wrongAccount")} />
            <Button className="mt-4" variant="secondary" onClick={auth.logout}>{t("googleAuth.switchAccount")}</Button>
          </> : <form className="space-y-4" onSubmit={onLink}>
            <p className="text-sm leading-6 text-platforma-subtle">{t("googleAuth.linkText")}</p>
            <Input label={t("auth.password")} type="password" autoComplete="current-password" required value={password} onChange={event => setPassword(event.target.value)} disabled={busy} />
            {mfaEnabled ? <>
              <Input label={t("googleAuth.mfaCode")} autoComplete="one-time-code" required value={mfaCode} onChange={event => setMfaCode(event.target.value)} disabled={busy} />
              <p className="text-sm text-platforma-subtle">{t("googleAuth.mfaHint")}</p>
            </> : null}
            <Button type="submit" className="w-full" isLoading={busy} disabled={mfaEnabled === undefined}>{t("googleAuth.linkSubmit")}</Button>
            {mfaEnabled === undefined ? <Button type="button" variant="secondary" onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button> : null}
            <Button type="button" variant="secondary" disabled={busy} onClick={auth.logout}>{t("googleAuth.switchAccount")}</Button>
          </form>}
        </>}
        <Link to="/login" className="platforma-focus-ring mt-6 block rounded-control text-center text-sm font-semibold text-brand-700 underline">{t("passwordReset.backToLogin")}</Link>
      </>}
    </section>
  </main>;
}

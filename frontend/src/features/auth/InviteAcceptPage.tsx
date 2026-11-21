import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useParams } from "react-router";
import { z } from "zod";
import { getApiErrorMessage, getApiFieldErrors } from "../../api/client";
import { normalizeAppError } from "../../api/appError";
import { teamApi } from "../../api/team";
import { LanguageSelector } from "../../components/layout/LanguageSelector";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { StatusNotice } from "../../components/ui/StatusNotice";
import { useI18n } from "../../lib/i18n";
import { useAuth } from "./AuthProvider";
import { MfaPage } from "./MfaPage";
import { PasswordVisibilityToggle } from "./PasswordVisibilityToggle";
import { useInvitationEntry } from "./useInvitationEntry";
import { useUnsavedEntryWarning } from "./useUnsavedEntryWarning";
import "./authLoginSerenity.css";

type FormValues = { full_name: string; phone: string; password: string; password_confirm: string };
const emptyForm = { full_name: "", phone: "", password: "", password_confirm: "" };

export function InviteAcceptPage() {
  const { token = "" } = useParams();
  return <InvitationForm key={token} token={token} />;
}

function InvitationForm({ token }: { token: string }) {
  const { t, language } = useI18n();
  const locale = language === "kk" ? "kk-KZ" : language === "en" ? "en-US" : "ru-RU";
  const { isAuthenticated, isLoading: isAuthLoading, user, logout } = useAuth();
  const [clock, setClock] = useState(Date.now());
  const [showPassword, setShowPassword] = useState(false);
  const preview = useQuery({ queryKey: ["team-invitation-preview", token], queryFn: () => teamApi.previewInvitation(token),
    enabled: Boolean(token), retry: false, refetchOnWindowFocus: false });
  const entry = useInvitationEntry(token, preview.data);
  const existing = Boolean(preview.data?.requires_authentication || entry.hasAccepted || entry.needsLogin);
  const schema = z.object({ full_name: z.string(), phone: z.string(),
    password: z.string().min(existing ? 1 : 8, t(existing ? "validation.passwordRequired" : "validation.passwordMin")), password_confirm: z.string(),
  }).refine(values => existing || values.password === values.password_confirm, { message: t("passwordReset.passwordMismatch"), path: ["password_confirm"] });
  const form = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: emptyForm });
  useUnsavedEntryWarning(form.formState.isDirty || entry.mutation.isPending);
  useEffect(() => { const timer = window.setInterval(() => setClock(Date.now()), 1000); return () => window.clearInterval(timer); }, []);
  useEffect(() => { if (preview.data?.full_name && !form.getFieldState("full_name").isDirty) form.resetField("full_name", { defaultValue: preview.data.full_name }); }, [preview.data?.full_name, form]);
  const matched = Boolean(isAuthenticated && user?.email.trim().toLowerCase() === preview.data?.email.trim().toLowerCase());
  const expired = preview.data?.status === "expired" || (preview.data?.status === "pending" && !entry.hasAccepted && new Date(preview.data.expires_at).getTime() <= clock);
  const usable = Boolean(preview.data && !expired && preview.data.status !== "revoked" && !preview.isError);
  const fieldErrors = getApiFieldErrors(entry.mutation.error);
  const invalidLink = [400, 404].includes(normalizeAppError(preview.error).status || 0);

  return <main className="serenity-login serenity-login--signal-field serenity-login--invitation">
    <div className="serenity-login__ambient" aria-hidden="true"><span /><span /><span /><span /><span /></div>
    {preview.isLoading || isAuthLoading ? <LoadingState scope="page" /> : <section className="mx-auto w-full max-w-xl rounded-panel border border-platforma-border bg-surface-card p-5 sm:p-8">
      <header className="mb-6 flex items-center justify-between gap-4">
        <img src="/brand/platforma-crm-logo-transparent.png" alt="PlatformaCRM" width={150} height={50} className="h-auto w-32 sm:w-36" />
        <LanguageSelector />
      </header>
      <p className="text-sm text-platforma-subtle">{t("invite.eyebrow")}</p>
      <h1 className="mt-2 break-words text-2xl font-semibold text-platforma-ink">{preview.data?.business_name || "PlatformaCRM"}</h1>
      {!token && <StatusNotice className="mt-5" tone="warning" title={t("invite.missing")} description={t("invite.askOwner")} />}
      {preview.isError && invalidLink && <StatusNotice className="mt-5" tone="warning" title={t("invite.invalid")} description={t("invite.askOwner")} />}
      {preview.isError && !invalidLink && <div className="mt-5"><ErrorState error={preview.error} message={t("invite.loadFailed")} action={<Button isLoading={preview.isFetching} onClick={() => void preview.refetch()}>{t("common.retry")}</Button>} /></div>}
      {(expired || preview.data?.status === "revoked") && <StatusNotice className="mt-5" tone="warning" title={t(expired ? "invite.expired" : "invite.revoked")} description={t("invite.askOwner")} />}
      {usable && <>
        <dl className="my-5 space-y-3 border-y border-platforma-border py-4 text-sm">
          <div><dt className="text-platforma-subtle">{t("invite.email")}</dt><dd className="mt-1 break-all font-semibold">{preview.data?.email}</dd></div>
          <div><dt className="text-platforma-subtle">{t("invite.assignedRole")}</dt><dd className="mt-1 font-semibold">{preview.data?.role_name || t(`settings.role.${preview.data?.role}`)}</dd></div>
        </dl>
        {!entry.hasAccepted && <p className="mb-4 text-xs text-platforma-subtle">{t("invite.expires", { date: new Date(preview.data!.expires_at).toLocaleString(locale, { dateStyle: "medium", timeStyle: "short" }) })}</p>}
        {entry.mfa ? <MfaPage embedded onComplete={entry.completeMfa} /> : <>
          {entry.mutation.isError && <ErrorState error={entry.mutation.error} message={getApiErrorMessage(entry.mutation.error)} />}
          {isAuthenticated && !matched ? <div className="space-y-4">
            <StatusNotice compact tone="warning" title={t("invite.wrongAccountTitle")} description={t("invite.currentAccount", { email: user?.email || "" })} />
            <p className="text-sm text-platforma-subtle">{t("invite.wrongAccount")}</p>
            <Button className="w-full" onClick={() => { entry.mutation.reset(); logout(); }}>{t("invite.signOutCurrent")}</Button>
          </div> : matched ? <Button className="mt-4 w-full" isLoading={entry.mutation.isPending} onClick={() => entry.mutation.mutate({ authenticated: true })}>{t(entry.hasAccepted ? "invite.retryEntry" : "invite.accept")}</Button>
          : <form className="mt-5 space-y-4" onSubmit={form.handleSubmit(values => entry.mutation.mutate({ values }))}>
            <p className="text-sm text-platforma-subtle">{t(existing ? "invite.inlineLoginHelp" : "invite.newAccountHelp")}</p>
            <fieldset disabled={entry.mutation.isPending} className="space-y-4">
              <input type="hidden" autoComplete="username" value={preview.data?.email || ""} readOnly />
              {!existing && <>
                <Input label={t("invite.name")} autoComplete="name" {...form.register("full_name")} error={fieldErrors.full_name?.join(" ")} />
                <Input label={t("invite.phone")} type="tel" autoComplete="tel" {...form.register("phone")} error={fieldErrors.phone?.join(" ")} />
              </>}
              <Input label={t(existing ? "auth.password" : "invite.newPassword")} type={showPassword ? "text" : "password"} autoComplete={existing ? "current-password" : "new-password"} rightIcon={<PasswordVisibilityToggle visible={showPassword} onToggle={() => setShowPassword(value => !value)} />} error={form.formState.errors.password?.message || fieldErrors.password?.join(" ")} {...form.register("password")} />
              {!existing && <Input label={t("passwordReset.repeatPassword")} type="password" autoComplete="new-password" error={form.formState.errors.password_confirm?.message} {...form.register("password_confirm")} />}
              <Button className="w-full" type="submit" isLoading={entry.mutation.isPending}>{t(entry.hasAccepted ? "invite.signInAfterAccept" : "invite.acceptAndEnter")}</Button>
            </fieldset>
            {existing && <Link className="platforma-focus-ring inline-flex min-h-11 items-center rounded-control text-sm font-semibold text-brand-700" to="/forgot-password">{t("auth.forgotPassword")}</Link>}
          </form>}
        </>}
      </>}
    </section>}
  </main>;
}

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useLocation, useNavigate, useParams } from "react-router";
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
import { rememberInvitationBusiness } from "../../lib/invitationBusiness";
import { useAuth } from "./AuthProvider";

type FormValues = { full_name: string; phone: string; password: string; password_confirm: string };
const emptyForm = { full_name: "", phone: "", password: "", password_confirm: "" };

export function InviteAcceptPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { token = "" } = useParams();
  const { t, language } = useI18n();
  const locale = language === "kk" ? "kk-KZ" : language === "en" ? "en-US" : "ru-RU";
  const { isAuthenticated, isLoading: isAuthLoading, user, refreshUser, logout } = useAuth();
  const [clock, setClock] = useState(Date.now());
  const schema = z.object({
    full_name: z.string(), phone: z.string(),
    password: z.string().min(8, t("validation.passwordMin")),
    password_confirm: z.string().min(1, t("passwordReset.repeatPasswordRequired")),
  }).refine(values => values.password === values.password_confirm, {
    message: t("passwordReset.passwordMismatch"), path: ["password_confirm"],
  });
  const form = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: emptyForm });
  const preview = useQuery({
    queryKey: ["team-invitation-preview", token],
    queryFn: () => teamApi.previewInvitation(token),
    enabled: Boolean(token), retry: false, refetchOnWindowFocus: false,
  });
  useEffect(() => {
    const timer = window.setInterval(() => setClock(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);
  useEffect(() => { form.reset(emptyForm); }, [token, form]);
  useEffect(() => {
    if (preview.data?.full_name && !form.getFieldState("full_name").isDirty) form.setValue("full_name", preview.data.full_name);
  }, [preview.data?.full_name, form]);
  const isInvitedAccount = Boolean(isAuthenticated && user?.email.trim().toLowerCase() === preview.data?.email.trim().toLowerCase());
  const acceptMutation = useMutation({
    mutationFn: (values: Partial<FormValues>) => teamApi.acceptInvitation({ token, ...values }),
    onSuccess: () => { form.reset(emptyForm); void preview.refetch(); },
    onError: () => { void preview.refetch(); },
  });
  const enterMutation = useMutation({
    mutationFn: async () => {
      const current = await refreshUser();
      const businessId = acceptMutation.data?.business ?? preview.data?.business;
      if (!current || !businessId || !current.businesses.some(business => String(business.id) === String(businessId))) {
        throw new Error(t("invite.accessUnavailable"));
      }
      rememberInvitationBusiness(current.id, businessId);
      queryClient.clear();
      navigate("/app", { replace: true });
    },
  });
  const accepted = acceptMutation.isSuccess || preview.data?.status === "accepted";
  const expired = preview.data?.status === "expired" || (preview.data?.status === "pending" && new Date(preview.data.expires_at).getTime() <= clock);
  const pending = preview.data?.status === "pending" && !expired && !accepted && !preview.isError;
  const fieldErrors = getApiFieldErrors(acceptMutation.error);
  const invalidLink = [400, 404].includes(normalizeAppError(preview.error).status || 0);
  const loginState = { from: { pathname: location.pathname }, email: preview.data?.email };
  const loginLink = <Link to="/login" state={loginState} className="platforma-focus-ring block rounded-control bg-brand-500 px-5 py-3 text-center text-sm font-bold text-white hover:bg-brand-600">{t(accepted ? "invite.signInAfterAccept" : "invite.signInToAccept")}</Link>;

  if (preview.isLoading || isAuthLoading) return <LoadingState scope="page" />;

  return <main className="min-h-screen bg-soft-mesh px-4 py-8">
    <section className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-xl items-center">
      <div className="glass-panel min-w-0 w-full rounded-[2rem] p-6 sm:p-8">
        <div className="mb-6 flex justify-end"><LanguageSelector /></div>
        <p className="text-sm font-bold text-brand-700">{t("invite.eyebrow")}</p>
        <h1 className="mt-2 break-words text-3xl font-black text-midnight">{preview.data?.business_name || "PlatformaCRM"}</h1>
        {!token && <StatusNotice className="mt-5" tone="warning" title={t("invite.missing")} description={t("invite.askOwner")} />}
        {preview.isError && invalidLink && !accepted && <StatusNotice className="mt-5" tone="warning" title={t("invite.invalid")} description={t("invite.askOwner")} />}
        {preview.isError && !invalidLink && !accepted && <div className="mt-5"><ErrorState error={preview.error} message={t("invite.loadFailed")}
          action={<Button type="button" isLoading={preview.isFetching} onClick={() => void preview.refetch()}>{t("common.retry")}</Button>} /></div>}
        {accepted ? <div className="mt-6 space-y-4">
          <StatusNotice tone="success" title={t("invite.accepted")} description={t("invite.acceptedHelp")} />
          {isInvitedAccount ? <>
            {enterMutation.isError && <ErrorState message={t("invite.accessUnavailable")} />}
            <Button className="w-full" type="button" isLoading={enterMutation.isPending} onClick={() => enterMutation.mutate()}>{t("invite.enter")}</Button>
          </> : isAuthenticated ? <>
            <ErrorState message={t("invite.wrongAccount")} />
            <Button className="w-full" type="button" onClick={logout}>{t("header.logout")}</Button>
          </> : loginLink}
        </div> : expired || preview.data?.status === "revoked" ? <StatusNotice className="mt-5" tone="warning"
          title={t(expired ? "invite.expired" : "invite.revoked")} description={t("invite.askOwner")} /> : null}
        {pending && <>
          <div className="mt-5 rounded-control border border-platforma-border bg-surface-muted p-4">
            <p className="text-sm font-bold text-platforma-ink">{t("invite.assignedRole")}: {t(`settings.role.${preview.data?.role}`)}</p>
            <p className="mt-1 text-sm text-platforma-subtle">{t(`settings.roleDescription.${preview.data?.role}`)}</p>
            <p className="mt-3 text-xs text-platforma-subtle">{t("invite.expires", { date: new Date(preview.data!.expires_at).toLocaleString(locale) })}</p>
          </div>
          {acceptMutation.isError && <div className="mt-5"><ErrorState error={acceptMutation.error} message={getApiErrorMessage(acceptMutation.error)} /></div>}
          {preview.data?.requires_authentication || isAuthenticated ? <div className="mt-6 space-y-4">
            <Input label={t("invite.email")} value={preview.data?.email || ""} readOnly />
            {!isAuthenticated ? <><p className="text-sm text-platforma-subtle">{t("invite.existingAccount")}</p>{loginLink}</> : !isInvitedAccount ? <>
              <ErrorState message={t("invite.wrongAccount")} />
              <Button className="w-full" type="button" onClick={logout}>{t("header.logout")}</Button>
            </> : <Button className="w-full" type="button" isLoading={acceptMutation.isPending} onClick={() => acceptMutation.mutate({})}>{t("invite.accept")}</Button>}
          </div> : <form className="mt-6 space-y-4" onSubmit={form.handleSubmit(values => acceptMutation.mutate(values))}>
            <p className="text-sm text-platforma-subtle">{t("invite.newAccountHelp")}</p>
            <fieldset disabled={acceptMutation.isPending} className="space-y-4">
              <Input label={t("invite.email")} value={preview.data?.email || ""} autoComplete="username" readOnly />
              <Input label={t("invite.name")} autoComplete="name" {...form.register("full_name")} error={fieldErrors.full_name?.join(" ")} />
              <Input label={t("invite.phone")} type="tel" autoComplete="tel" {...form.register("phone")} error={fieldErrors.phone?.join(" ")} />
              <Input label={t("invite.newPassword")} type="password" autoComplete="new-password" error={form.formState.errors.password?.message || fieldErrors.password?.join(" ")} {...form.register("password")} />
              <Input label={t("passwordReset.repeatPassword")} type="password" autoComplete="new-password" error={form.formState.errors.password_confirm?.message} {...form.register("password_confirm")} />
              <Button className="w-full" type="submit" isLoading={acceptMutation.isPending}>{t("invite.accept")}</Button>
            </fieldset>
          </form>}
        </>}
        {!accepted && <Link to="/login" state={pending ? loginState : undefined} className="platforma-focus-ring mt-4 block rounded-control py-2 text-center text-sm font-bold text-brand-700">{t("invite.login")}</Link>}
      </div>
    </section>
  </main>;
}

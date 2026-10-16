import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { recoveryApi } from "../../api/recovery";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { LanguageSelector } from "../../components/layout/LanguageSelector";
import { useI18n } from "../../lib/i18n";

export function AccountRecoveryPage() {
  const { t } = useI18n();
  const [credentials] = useState(() => window.location.hash.slice(1).split("/"));
  const [password, setPassword] = useState("");
  const [repeat, setRepeat] = useState("");
  const hasLink = credentials.length === 2 && /^[0-9a-f-]{36}$/.test(credentials[0]) && /^[A-Za-z0-9_-]{43}$/.test(credentials[1]);
  useEffect(() => { if (window.location.hash) window.history.replaceState(null, "", window.location.pathname); }, []);
  const contact = useQuery({ queryKey: ["recovery-contact"], queryFn: recoveryApi.contact, retry: false, enabled: !hasLink });
  const mutation = useMutation({ mutationFn: () => recoveryApi.complete(credentials[0], credentials[1], password), retry: false,
    onSuccess: () => { setPassword(""); setRepeat(""); } });
  return <main className="grid min-h-screen place-items-center bg-soft-mesh px-4 py-8">
    <section className="glass-panel w-full max-w-lg space-y-5 rounded-2xl p-6 sm:p-8">
      <LanguageSelector />
      <h1 className="text-2xl font-semibold">{t("recovery.title")}</h1>
      {mutation.isSuccess ? <p role="status">{t("recovery.done")}</p> : hasLink ? <form className="space-y-4" onSubmit={event => { event.preventDefault(); if (password === repeat && password.length >= 8 && !mutation.isPending) mutation.mutate(); }}>
        <p className="text-sm">{t("recovery.effects")}</p>
        <Input label={t("invite.newPassword")} type="password" autoComplete="new-password" minLength={8} maxLength={128} required disabled={mutation.isPending} value={password} onChange={event => setPassword(event.target.value)} />
        <Input label={t("passwordReset.repeatPassword")} type="password" autoComplete="new-password" minLength={8} maxLength={128} required disabled={mutation.isPending} value={repeat} onChange={event => setRepeat(event.target.value)} />
        {repeat && password !== repeat && <p role="alert">{t("passwordReset.passwordMismatch")}</p>}
        {mutation.error && <ErrorState error={mutation.error} />}
        <Button type="submit" isLoading={mutation.isPending} disabled={mutation.isPending || password !== repeat || password.length < 8}>{t("recovery.complete")}</Button>
      </form> : <>
        <p className="text-sm">{t("recovery.contactInstructions")}</p>
        {contact.isPending && <LoadingState />}
        {contact.error && <ErrorState error={contact.error} action={<Button onClick={() => contact.refetch()}>{t("common.retry")}</Button>} />}
        {contact.data?.support_email ? <a className="platforma-focus-ring inline-flex min-h-11 items-center break-all text-brand-700" href={`mailto:${contact.data.support_email}`}>{contact.data.support_email}</a> : contact.isSuccess && <p role="status">{t("recovery.contactUnavailable")}</p>}
      </>}
      <Link className="platforma-focus-ring inline-flex min-h-10 items-center text-brand-700" to="/login">{t("passwordReset.backToLogin")}</Link>
    </section>
  </main>;
}

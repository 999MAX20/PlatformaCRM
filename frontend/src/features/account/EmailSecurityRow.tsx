import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Mail } from "lucide-react";
import { useState } from "react";
import { confirmEmailChange, getMfaStatus, requestEmailChange } from "../../api/auth";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { useI18n } from "../../lib/i18n";
import { SecuritySettingRow } from "./SecuritySettingRow";
import { useAuth } from "../auth/AuthProvider";

export function EmailSecurityRow() {
  const queryClient = useQueryClient();
  const { user, refreshUser } = useAuth();
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [sent, setSent] = useState(false);
  const [saved, setSaved] = useState(false);
  const [form, setForm] = useState({ new_email: "", current_password: "", mfa_code: "" });
  const [code, setCode] = useState("");
  const mfa = useQuery({ queryKey: ["mfa-status"], queryFn: getMfaStatus, enabled: Boolean(user?.id) });
  const request = useMutation({ mutationFn: () => requestEmailChange(form), onSuccess: () => { setSent(true); setForm(value => ({ ...value, current_password: "", mfa_code: "" })); } });
  const confirm = useMutation({ mutationFn: () => confirmEmailChange(code), onSuccess: async () => { setOpen(false); setCode(""); setSaved(true); await refreshUser(); await queryClient.invalidateQueries({ queryKey: ["account-sessions"] }); } });
  const busy = request.isPending || confirm.isPending;
  const close = () => { if (!busy) { setOpen(false); setForm({ new_email: "", current_password: "", mfa_code: "" }); setCode(""); } };
  return <>
    <SecuritySettingRow icon={<Mail size={18} />} title={t("account.emailLogin")} value={user?.email}
      action={<Button size="sm" variant="secondary" aria-label={t("account.emailChange")} onClick={() => { setSent(false); setSaved(false); request.reset(); confirm.reset(); setOpen(true); }}>{t("account.securityEdit")}</Button>} />
    {saved ? <p role="status" className="mb-3 text-sm text-emerald-700">{t("account.emailSaved")}</p> : null}
    <Modal title={t("account.emailChange")} open={open} onClose={close} size="sm">
      <form className="space-y-4" onSubmit={event => { event.preventDefault(); if (sent) confirm.mutate(); else request.mutate(); }}>
        {sent ? <>
          <p className="break-words text-sm">{t("account.emailCodeSent")} {form.new_email}</p>
          <Input label={t("account.emailCode")} inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} required disabled={busy} value={code} onChange={event => setCode(event.target.value)} />
          <Button type="button" variant="ghost" disabled={busy} onClick={() => { setSent(false); setCode(""); confirm.reset(); request.reset(); }}>{t("account.emailRestart")}</Button>
        </> : <>
          <Input label={t("account.emailNew")} type="email" autoComplete="email" maxLength={254} required disabled={busy} value={form.new_email} onChange={event => setForm(value => ({ ...value, new_email: event.target.value }))} />
          <Input label={t("account.currentPassword")} type="password" autoComplete="current-password" required disabled={busy} value={form.current_password} onChange={event => setForm(value => ({ ...value, current_password: event.target.value }))} />
          {mfa.data?.enabled ? <Input label={t("mfa.codeLabel")} autoComplete="one-time-code" required disabled={busy} value={form.mfa_code} onChange={event => setForm(value => ({ ...value, mfa_code: event.target.value }))} /> : null}
        </>}
        {request.error || confirm.error ? <p role="alert" className="text-sm text-platforma-danger">{getApiErrorMessage(request.error || confirm.error)}</p> : null}
        <div className="flex justify-end gap-2"><Button type="button" variant="secondary" disabled={busy} onClick={close}>{t("common.cancel")}</Button><Button type="submit" isLoading={busy}>{t(sent ? "common.save" : "account.emailSendCode")}</Button></div>
      </form>
    </Modal>
  </>;
}

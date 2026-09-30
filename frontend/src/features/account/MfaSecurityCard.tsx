import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, KeyRound, LogOut, ShieldCheck, ShieldOff } from "lucide-react";
import { useState } from "react";

import {
  confirmMfaEnrollment,
  disableMfa,
  getMfaStatus,
  isMfaPendingResponse,
  regenerateMfaRecoveryCodes,
  revokeMfaSessions,
  startMfaEnrollment,
  type MfaEnrollment,
} from "../../api/auth";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { ErrorState } from "../../components/ui/StateViews";
import { StatusNotice } from "../../components/ui/StatusNotice";
import { useI18n } from "../../lib/i18n";

type Mode = "setup" | "recovery" | "disable" | "sessions" | null;

export function MfaSecurityCard() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const statusQuery = useQuery({ queryKey: ["mfa-status"], queryFn: getMfaStatus });
  const [mode, setMode] = useState<Mode>(null);
  const [enrollment, setEnrollment] = useState<MfaEnrollment | null>(null);
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [reason, setReason] = useState("");
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);

  const startMutation = useMutation({
    mutationFn: () => startMfaEnrollment(),
    onSuccess: (data) => {
      setEnrollment(data);
      setMode("setup");
    },
  });
  const actionMutation = useMutation({
    mutationFn: async () => {
      if (mode === "setup" && enrollment) {
        const result = await confirmMfaEnrollment(enrollment.challenge_token, code);
        return { recovery_codes: result.recovery_codes || [] };
      }
      if (mode === "recovery") return regenerateMfaRecoveryCodes(code);
      if (mode === "disable") {
        const result = await disableMfa({ password, code, reason });
        if (isMfaPendingResponse(result)) {
          sessionStorage.setItem("zani_mfa_pending", JSON.stringify(result));
          window.location.assign("/mfa");
        }
        return { recovery_codes: [] };
      }
      if (mode === "sessions") {
        await revokeMfaSessions(code);
        return { recovery_codes: [] };
      }
      return { recovery_codes: [] };
    },
    onSuccess: async (data) => {
      setRecoveryCodes(data.recovery_codes || []);
      await queryClient.invalidateQueries({ queryKey: ["mfa-status"] });
      if (!data.recovery_codes?.length) closeModal();
    },
  });

  const mfa = statusQuery.data;
  if (!statusQuery.isLoading && mfa && !mfa.available) return null;

  function openMode(nextMode: Mode) {
    setCode("");
    setPassword("");
    setReason("");
    setRecoveryCodes([]);
    setEnrollment(null);
    setMode(nextMode);
  }

  function closeModal() {
    if (actionMutation.isPending) return;
    setMode(null);
    setEnrollment(null);
    setCode("");
    setPassword("");
    setReason("");
    setRecoveryCodes([]);
  }

  return (
    <>
      <div className="py-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div><p className="text-sm font-semibold">{t("mfa.accountTitle")}</p>
            {mfa ? <p className="text-xs text-platforma-subtle">{mfa.enabled ? t("mfa.enabled") : mfa.required ? t("mfa.required") : t("mfa.notEnabled")}</p> : null}
          </div>
          {statusQuery.isLoading ? <span role="status" className="text-sm">{t("common.loading")}</span> : mfa && !mfa.enabled ? <Button size="sm" type="button" isLoading={startMutation.isPending} onClick={() => startMutation.mutate()}><ShieldCheck size={16} />{t("mfa.setup")}</Button> : null}
        </div>
        {statusQuery.error || startMutation.error || actionMutation.error ? <div className="mt-2"><ErrorState message={getApiErrorMessage(statusQuery.error || startMutation.error || actionMutation.error)} /></div> : null}
        {mfa?.enabled ? <details className="mt-2">
          <summary className="cursor-pointer text-sm font-semibold">{t("mfa.accountEyebrow")}</summary>
          <div className="my-3 flex flex-wrap gap-x-4 gap-y-2 text-xs text-platforma-subtle"><span>{t("mfa.recoveryRemaining")}: {mfa.recovery_codes_remaining}</span><span>{t("mfa.activeSessions")}: {mfa.active_sessions}</span></div>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="secondary" onClick={() => openMode("recovery")}><KeyRound size={16} />{t("mfa.newRecoveryCodes")}</Button>
            <Button size="sm" variant="warning" onClick={() => openMode("sessions")}><LogOut size={16} />{t("mfa.revokeSessions")}</Button>
            <Button size="sm" variant="warning" onClick={() => openMode("disable")}><ShieldOff size={16} />{t("mfa.disable")}</Button>
          </div>
        </details> : null}
      </div>

      <Modal title={modalTitle(mode, t)} open={Boolean(mode)} onClose={closeModal}>
        <div className="grid gap-4 rounded-3xl bg-white p-4 sm:p-5">
          {recoveryCodes.length ? (
            <>
              <StatusNotice tone="warning" title={t("mfa.recoveryWarning")} />
              <div className="grid grid-cols-2 gap-2 rounded-2xl bg-slate-950 p-4 font-mono text-sm text-white">{recoveryCodes.map((item) => <span key={item}>{item}</span>)}</div>
              <Button type="button" variant="secondary" onClick={() => navigator.clipboard.writeText(recoveryCodes.join("\n"))}><Copy size={17} />{t("mfa.copyCodes")}</Button>
              <Button type="button" onClick={closeModal}>{t("common.close")}</Button>
            </>
          ) : (
            <form className="grid gap-4" onSubmit={(event) => { event.preventDefault(); actionMutation.mutate(); }}>
              {mode === "setup" && enrollment ? (
                <div className="grid gap-2 rounded-2xl bg-slate-50 p-4">
                  <p className="text-sm font-semibold leading-6 text-slate-600">{t("mfa.addAuthenticatorText")}</p>
                  <code className="break-all rounded-xl bg-white px-3 py-2 text-sm font-black text-midnight">{enrollment.manual_key}</code>
                  <a className="text-sm font-black text-brand-700" href={enrollment.otpauth_uri}>{t("mfa.openAuthenticator")}</a>
                </div>
              ) : null}
              {mode === "disable" ? (
                <>
                  <Input label={t("account.currentPassword")} type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
                  <Input label={t("mfa.disableReason")} value={reason} onChange={(event) => setReason(event.target.value)} minLength={8} required />
                </>
              ) : null}
              <Input label={t("mfa.codeLabel")} value={code} onChange={(event) => setCode(event.target.value)} autoComplete="one-time-code" placeholder={t("mfa.codePlaceholder")} required={mode !== "sessions" || Boolean(mfa?.enabled)} />
              <div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={closeModal}>{t("common.cancel")}</Button><Button type="submit" variant={mode === "disable" || mode === "sessions" ? "warning" : "primary"} isLoading={actionMutation.isPending}>{t("common.save")}</Button></div>
            </form>
          )}
        </div>
      </Modal>
    </>
  );
}

function modalTitle(mode: Mode, t: (key: string) => string) {
  if (mode === "setup") return t("mfa.setup");
  if (mode === "recovery") return t("mfa.newRecoveryCodes");
  if (mode === "sessions") return t("mfa.revokeSessions");
  if (mode === "disable") return t("mfa.disable");
  return t("mfa.accountTitle");
}

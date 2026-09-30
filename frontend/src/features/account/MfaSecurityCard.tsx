import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, KeyRound, ShieldCheck, ShieldOff } from "lucide-react";
import { useState } from "react";

import {
  confirmMfaEnrollment,
  disableMfa,
  getMfaStatus,
  isMfaPendingResponse,
  regenerateMfaRecoveryCodes,
  startMfaEnrollment,
  type MfaEnrollment,
} from "../../api/auth";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { ErrorState } from "../../components/ui/StateViews";
import { StatusNotice } from "../../components/ui/StatusNotice";
import { SecuritySettingRow } from "./SecuritySettingRow";
import { useI18n } from "../../lib/i18n";
import { AuthenticatorEnrollment } from "../auth/AuthenticatorEnrollment";

type Mode = "setup" | "recovery" | "disable" | null;

export function MfaSecurityCard() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const statusQuery = useQuery({ queryKey: ["mfa-status"], queryFn: getMfaStatus });
  const [manageOpen, setManageOpen] = useState(false);
  const [mode, setMode] = useState<Mode>(null);
  const [enrollment, setEnrollment] = useState<MfaEnrollment | null>(null);
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [reason, setReason] = useState("");
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);

  const startMutation = useMutation({
    mutationFn: () => startMfaEnrollment(),
    onSuccess: (data) => {
      actionMutation.reset();
      setCode("");
      setRecoveryCodes([]);
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
      return { recovery_codes: [] };
    },
    onSuccess: async (data) => {
      setRecoveryCodes(data.recovery_codes || []);
      await queryClient.invalidateQueries({ queryKey: ["mfa-status"] });
      await queryClient.invalidateQueries({ queryKey: ["account-sessions"] });
      if (!data.recovery_codes?.length) closeModal();
    },
  });

  const mfa = statusQuery.data;
  if (!statusQuery.isLoading && mfa && !mfa.available) return null;

  function openMode(nextMode: Mode) {
    actionMutation.reset();
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
      <div>
        <SecuritySettingRow icon={<ShieldCheck size={18} />} title={t("mfa.accountTitle")}
          value={mfa ? <span className={mfa.enabled ? "text-emerald-700" : "text-platforma-subtle"}>{mfa.enabled ? t("mfa.enabled") : mfa.required ? t("mfa.required") : t("mfa.notEnabled")}</span> : undefined}
          action={statusQuery.isLoading ? <span role="status" className="text-sm">{t("common.loading")}</span> : mfa ? <Button size="sm" variant="secondary" aria-label={t(mfa.enabled ? "mfa.accountEyebrow" : "mfa.setup")} isLoading={startMutation.isPending} onClick={() => mfa.enabled ? setManageOpen(value => !value) : startMutation.mutate()}>{t(mfa.enabled ? "account.securityManage" : "account.securityConnect")}</Button> : <Button size="sm" variant="secondary" onClick={() => void statusQuery.refetch()}>{t("common.retry")}</Button>} />
        {statusQuery.error || startMutation.error ? <div className="mt-2"><ErrorState message={getApiErrorMessage(statusQuery.error || startMutation.error)} /></div> : null}
        {mfa?.enabled && manageOpen ? <div className="pb-3 pl-12">
          <div className="my-3 flex flex-wrap gap-x-4 gap-y-2 text-xs text-platforma-subtle"><span>{t("mfa.recoveryRemaining")}: {mfa.recovery_codes_remaining}</span></div>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="secondary" onClick={() => openMode("recovery")}><KeyRound size={16} />{t("mfa.newRecoveryCodes")}</Button>
            <Button size="sm" variant="warning" onClick={() => openMode("disable")}><ShieldOff size={16} />{t("mfa.disable")}</Button>
          </div>
        </div> : null}
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
              {actionMutation.error ? <ErrorState message={getApiErrorMessage(actionMutation.error)} /> : null}
              {mode === "setup" && enrollment ? (
                <AuthenticatorEnrollment enrollment={enrollment} />
              ) : null}
              {mode === "disable" ? (
                <>
                  <Input label={t("account.currentPassword")} type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
                  <Input label={t("mfa.disableReason")} value={reason} onChange={(event) => setReason(event.target.value)} minLength={8} required />
                </>
              ) : null}
              <div className={mode === "setup" ? "mx-auto w-48 max-w-full text-center" : undefined}>
                <Input label={t("mfa.codeLabel")} value={code} onChange={(event) => setCode(event.target.value)} autoComplete="one-time-code" inputMode={mode === "setup" ? "numeric" : "text"} pattern={mode === "setup" ? "[0-9]{6}" : undefined} maxLength={mode === "setup" ? 6 : undefined} placeholder={mode === "setup" ? "000000" : t("mfa.codePlaceholder")} className={mode === "setup" ? "text-center font-mono text-lg tracking-[0.25em]" : undefined} required />
              </div>
              <div className={`flex gap-2 ${mode === "setup" ? "justify-center" : "justify-end"}`}>
                {mode !== "setup" ? <Button type="button" variant="secondary" onClick={closeModal}>{t("common.cancel")}</Button> : null}
                <Button type="submit" variant={mode === "disable" ? "warning" : "primary"} isLoading={actionMutation.isPending}>{t(mode === "setup" ? "mfa.enable" : "common.save")}</Button>
              </div>
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
  if (mode === "disable") return t("mfa.disable");
  return t("mfa.accountTitle");
}

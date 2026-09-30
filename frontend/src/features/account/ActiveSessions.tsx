import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Monitor, Smartphone } from "lucide-react";
import { useState } from "react";
import { getAccountSessions, getMfaStatus, revokeAccountSession, revokeMfaSessions, type AccountSession } from "../../api/auth";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { ErrorState } from "../../components/ui/StateViews";
import { formatDateTime } from "../../lib/format";
import { useI18n } from "../../lib/i18n";
import { useAuth } from "../auth/AuthProvider";

function deviceName(agent: string, fallback: string) {
  const browser = /Edg\//.test(agent) ? "Edge" : /OPR\//.test(agent) ? "Opera" : /Firefox\/|FxiOS\//.test(agent) ? "Firefox" : /Chrome\/|CriOS\//.test(agent) ? "Chrome" : /Safari\//.test(agent) ? "Safari" : "";
  const system = /Android/.test(agent) ? "Android" : /iPhone|iPad/.test(agent) ? "iOS" : /Windows/.test(agent) ? "Windows" : /Macintosh/.test(agent) ? "macOS" : /Linux/.test(agent) ? "Linux" : "";
  return [browser, system].filter(Boolean).join(" · ") || fallback;
}

export function ActiveSessions() {
  const { t } = useI18n();
  const { user } = useAuth();
  const client = useQueryClient();
  const sessions = useQuery({ queryKey: ["account-sessions", user?.id], queryFn: getAccountSessions, enabled: Boolean(user?.id), refetchInterval: 60_000 });
  const mfa = useQuery({ queryKey: ["mfa-status"], queryFn: getMfaStatus });
  const [target, setTarget] = useState<AccountSession | "others" | null>(null);
  const [code, setCode] = useState("");
  const mutation = useMutation({
    mutationFn: async () => {
      if (target === "others") await revokeMfaSessions(code);
      else if (target) await revokeAccountSession(target.id, code);
    },
    onSuccess: async () => {
      setTarget(null); setCode("");
      await Promise.all([client.invalidateQueries({ queryKey: ["account-sessions"] }), client.invalidateQueries({ queryKey: ["mfa-status"] })]);
    },
  });
  const others = (sessions.data?.sessions.filter(session => !session.is_current).length || 0) + (sessions.data?.legacy_count || 0);
  function open(session: AccountSession | "others") { mutation.reset(); setCode(""); setTarget(session); }
  return <section className="mt-2 border-t border-platforma-border pt-4" aria-labelledby="active-sessions-title">
    <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
      <h3 id="active-sessions-title" className="text-sm font-semibold">{t("account.sessionsTitle")}</h3>
      {others > 0 ? <Button size="sm" variant="ghost" onClick={() => open("others")}>{t("account.sessionsEndOthers")}</Button> : null}
    </div>
    {sessions.isLoading ? <p role="status" className="py-3 text-sm text-platforma-subtle">{t("common.loading")}</p> : sessions.error ? <ErrorState message={getApiErrorMessage(sessions.error)} action={<Button size="sm" variant="secondary" onClick={() => void sessions.refetch()}>{t("common.retry")}</Button>} /> : !sessions.data?.available ? <p className="py-2 text-sm text-platforma-subtle">{t("account.sessionsUnavailable")}</p> : <div className="divide-y divide-platforma-border">
      {sessions.data.sessions.map(session => <div key={session.id} className="flex items-center justify-between gap-3 py-3" data-testid="account-session">
        <div className="flex min-w-0 items-center gap-3">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-platforma-bg text-platforma-subtle" aria-hidden="true">{/Android|iPhone|iPad/.test(session.user_agent) ? <Smartphone size={19} /> : <Monitor size={19} />}</span>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1"><span className="text-sm font-medium">{deviceName(session.user_agent, t("account.sessionsUnknown"))}</span>{session.is_current ? <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700">{t("account.sessionsCurrent")}</span> : null}</div>
            <p className="mt-1 text-xs text-platforma-subtle">{t("account.sessionsLastSeen")}: {formatDateTime(session.last_seen_at)}</p>
            {session.ip_address ? <p className="mt-0.5 break-all text-xs text-platforma-subtle">IP: {session.ip_address}</p> : null}
          </div>
        </div>
        {!session.is_current ? <Button size="sm" variant="ghost" className="shrink-0" aria-label={`${t("account.sessionsEnd")} ${deviceName(session.user_agent, t("account.sessionsUnknown"))}`} onClick={() => open(session)}>{t("account.sessionsEnd")}</Button> : null}
      </div>)}
    </div>}
    <Modal title={t(target === "others" ? "account.sessionsEndOthers" : "account.sessionsEnd")} open={target !== null} onClose={() => { if (!mutation.isPending) { setTarget(null); setCode(""); } }} size="sm">
      <form className="space-y-4" onSubmit={event => { event.preventDefault(); mutation.mutate(); }}>
        {target && target !== "others" ? <p className="text-sm font-semibold">{deviceName(target.user_agent, t("account.sessionsUnknown"))}</p> : null}
        <p className="text-sm text-platforma-subtle">{t(target === "others" ? "account.sessionsConfirmOthers" : "account.sessionsConfirmOne")}</p>
        {mfa.isLoading ? <p role="status">{t("common.loading")}</p> : mfa.error ? <ErrorState message={getApiErrorMessage(mfa.error)} action={<Button type="button" variant="secondary" onClick={() => void mfa.refetch()}>{t("common.retry")}</Button>} /> : mfa.data?.enabled ? <Input label={t("mfa.codeLabel")} autoComplete="one-time-code" value={code} onChange={event => setCode(event.target.value)} required disabled={mutation.isPending} /> : null}
        {mutation.error ? <ErrorState message={getApiErrorMessage(mutation.error)} /> : null}
        <div className="flex justify-end gap-2"><Button type="button" variant="secondary" disabled={mutation.isPending} onClick={() => { setTarget(null); setCode(""); }}>{t("common.cancel")}</Button><Button type="submit" variant="warning" disabled={mfa.isLoading || Boolean(mfa.error)} isLoading={mutation.isPending}>{t("account.sessionsEnd")}</Button></div>
      </form>
    </Modal>
  </section>;
}

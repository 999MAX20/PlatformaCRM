import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import axios from "axios";
import { medicalParticipationApi as api, type ParticipationNotificationContext, type ParticipationWorkspaceAccess, type ProposalSourceScope } from "../../api/medicalParticipation";
import { getApiErrorMessage } from "../../api/client";
import { usePageHeader } from "../../components/layout/PageHeaderContext";
import { Button } from "../../components/ui/Button";
import { ErrorState, ForbiddenState, LoadingState } from "../../components/ui/StateViews";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useI18n } from "../../lib/i18n";
import { useAuth } from "../auth/AuthProvider";
import { ParticipationEntry } from "./ParticipationEntry";
import { SourceProposalEntry } from "./SourceProposalWorkspace";
import { ParticipationDeclineForm } from "./ParticipationDeclineForm";

export function ParticipationNotificationPage() {
  const { business, isLoading, error } = useActiveBusiness();
  const { user } = useAuth();
  const [params] = useSearchParams();
  const { t } = useI18n();
  const { setPageHeader } = usePageHeader();
  useEffect(() => { setPageHeader({ title: t("medical.participation.title") }); return () => setPageHeader(null); }, [setPageHeader, t]);
  const value = params.get("notification") ?? "";
  const notificationId = /^[1-9]\d*$/.test(value) && params.getAll("notification").length === 1 && Number.isSafeInteger(Number(value)) ? Number(value) : 0;
  if (!business || !user) return isLoading ? <LoadingState /> : error ? <ErrorState error={error} /> : <ForbiddenState />;
  return <NotificationWorkspace key={`${business.id}:${user.id}:${notificationId}`} businessId={Number(business.id)} notificationId={notificationId} />;
}

function NotificationWorkspace({ businessId, notificationId }: { businessId: number; notificationId: number }) {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [context, setContext] = useState<ParticipationNotificationContext | null>(null);
  const [access, setAccess] = useState<ParticipationWorkspaceAccess | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(Boolean(notificationId));
  const [pending, setPending] = useState(false);
  const [conflict, setConflict] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [declining, setDeclining] = useState(false);
  const declineGuard = useRef({ dirty: false, pending: false });
  const inFlight = useRef(false);
  const retry = useRef<{ fingerprint: string; key: string } | null>(null);
  const title = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    if (!notificationId) return;
    const controller = new AbortController();
    setLoading(true); setContext(null); setAccess(null); setError(null); setConflict(false);
    void Promise.all([api.notificationContext({ business_id: businessId, notification_id: notificationId }, controller.signal), api.access(businessId, controller.signal)])
      .then(([value, permissions]) => { if (!controller.signal.aborted) { setContext(value); setAccess(permissions); } })
      .catch(cause => { if (!controller.signal.aborted) setError(cause); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [businessId, notificationId, attempt]);
  useLayoutEffect(() => { if (context && !loading) title.current?.focus(); }, [context, loading]);
  const status = axios.isAxiosError(error) ? error.response?.status : undefined;
  const unavailable = !notificationId || [401, 403, 404].includes(status ?? 0);
  function refresh() { setDeclining(false); setContext(null); setAccess(null); setAttempt(value => value + 1); }
  async function respond(decision: "accept" | "decline") {
    if (!context || inFlight.current || conflict) return;
    const item = context.participation;
    const payload = { business_id: businessId, patient_id: item.patient_id, expected_revision: item.revision, decision };
    const fingerprint = JSON.stringify({ id: item.id, ...payload });
    if (retry.current?.fingerprint !== fingerprint) retry.current = { fingerprint, key: crypto.randomUUID() };
    inFlight.current = true; setPending(true); setError(null);
    try {
      await api.respond(item.id, payload, retry.current.key);
      refresh();
    } catch (cause) {
      setError(cause);
      const code = axios.isAxiosError(cause) ? cause.response?.status : undefined;
      if ([401, 403, 404].includes(code ?? 0)) { setContext(null); setAccess(null); }
      if (code === 409) setConflict(true);
    } finally { inFlight.current = false; setPending(false); }
  }
  const item = context?.participation;
  const actions = access?.branches.find(branch => branch.id === item?.branch_id)?.actions;
  const source: ProposalSourceScope | null = item && context?.direction === "outgoing" ? {
    business_id: businessId, patient_id: item.patient_id,
    ...(context.source_appointment_id ? { source_appointment_id: context.source_appointment_id }
      : context.source_participation_id ? { source_participation_id: context.source_participation_id } : {}),
  } : null;
  return <section className="max-w-3xl space-y-4" data-testid="participation-notification">
    <div className="flex flex-wrap gap-2">
      <Button variant="secondary" disabled={pending || declining} onClick={() => navigate("/app/notifications")}>{t("header.notifications")}</Button>
      {notificationId ? <Button variant="secondary" disabled={pending || loading || declining} onClick={refresh}>{t("medical.clinical.reload")}</Button> : null}
    </div>
    {loading ? <LoadingState /> : null}
    {unavailable ? <ErrorState message={t("medical.notifications.unavailable")} /> : error ?
      <ErrorState message={conflict ? t("medical.clinical.conflict") : getApiErrorMessage(error)} action={!item ? <Button variant="secondary" onClick={refresh}>{t("common.retry")}</Button> : undefined} /> : null}
    {!unavailable && item && access ? <div className="space-y-4">
      <div className="space-y-1 break-words">
        <h2 ref={title} tabIndex={-1} className="text-base font-semibold">{item.patient_name}</h2>
        <p className="text-sm">{item.member_name} · {item.branch_name}</p>
        <p role="status" className="text-sm text-platforma-subtle">{t(`medical.participation.state.${item.state}`)}</p>
        {item.decline_reason ? <p className="whitespace-pre-wrap text-sm">{t("medical.participation.declineReason")}: {item.decline_reason}</p> : null}
      </div>
      {declining ? <ParticipationDeclineForm businessId={businessId} item={item} guard={declineGuard} onSaved={refresh}
        onCancel={() => { setDeclining(false); title.current?.focus(); }}
        onDenied={cause => { setDeclining(false); setContext(null); setAccess(null); setError(cause); }} /> : <div className="flex flex-wrap gap-2">
        {context.direction === "incoming" && item.state === "pending" && item.member_id === access.member_id && actions?.approve ? <>
          <Button size="lg" disabled={pending || conflict} isLoading={pending} onClick={() => void respond("accept")}>{t("medical.participation.accept")}</Button>
          <Button size="lg" variant="secondary" disabled={pending || conflict} onClick={() => setDeclining(true)}>{t("medical.participation.decline")}</Button>
        </> : null}
        {!pending && !conflict ? source ? <SourceProposalEntry scope={source} /> :
          <ParticipationEntry businessId={businessId} patientId={item.patient_id} branchId={item.branch_id} onClosed={refresh} /> : null}
      </div>}
    </div> : null}
  </section>;
}

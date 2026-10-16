import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { recoveryApi, type RecoverySnapshot, type RecoveryRequest } from "../../api/recovery";
import { issueMfaStepUp } from "../../api/auth";
import { normalizeAppError } from "../../api/appError";
import { useActionConfirm } from "../../components/actions/ActionConfirmProvider";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { Textarea } from "../../components/ui/Textarea";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { RecoverySummary } from "../account/RecoverySummary";
import { PlatformLoadError } from "./PlatformData";
import { SupportCreateDialog } from "../support/SupportCreateDialog";

type Props = { business: string; onDraft: (value: { dirty: boolean; pending: boolean }) => void };
export function BusinessRecoveryPanel(props: Props) {
  const { t } = useI18n();
  const query = useQuery({ queryKey: ["platform-recovery", props.business], queryFn: () => recoveryApi.get(props.business), retry: false, gcTime: 0, refetchOnWindowFocus: false });
  if (query.isPending) return <LoadingState />;
  if (query.isError || !query.data) return <PlatformLoadError error={query.error} message={t("platform.merchantDetail.error")} onRetry={() => query.refetch()} />;
  return <RecoveryEditor {...props} data={query.data} reload={() => query.refetch()} />;
}

function RecoveryEditor({ business, onDraft, data, reload }: Props & { data: RecoverySnapshot; reload: () => Promise<unknown> }) {
  const { t } = useI18n();
  const confirm = useActionConfirm();
  const [userId, setUserId] = useState("");
  const [email, setEmail] = useState("");
  const [caseId, setCaseId] = useState("");
  const [reason, setReason] = useState("");
  const [reference, setReference] = useState("");
  const [verified, setVerified] = useState(false);
  const [mfa, setMfa] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [creatingCase, setCreatingCase] = useState(false);
  const candidate = data.candidates.find(row => String(row.id) === userId);
  const dirty = Boolean(userId || email || caseId || reason || reference || mfa);
  function clear() { setUserId(""); setEmail(""); setCaseId(""); setReason(""); setReference(""); setVerified(false); setMfa(""); }
  const mutation = useMutation({
    mutationFn: async (action: { type: "prepare" } | { type: "send" | "cancel"; item: RecoveryRequest }) => {
      const token = (await issueMfaStepUp(mfa)).step_up_token;
      return action.type === "prepare" ? recoveryApi.prepare(business, { user_id: Number(userId), new_email: email,
        support_case_id: Number(caseId), reason, verified_reference: reference, expected_revision: candidate!.revision }, token)
        : recoveryApi.act(business, action.item.id, action.type, token);
    }, retry: false,
    onSuccess: async () => { clear(); await reload(); },
    onError: () => setMfa(""),
  });
  const pending = mutation.isPending || refreshing;
  useEffect(() => { onDraft({ dirty, pending }); }, [dirty, pending, onDraft]);
  useEffect(() => () => onDraft({ dirty: false, pending: false }), [onDraft]);
  async function refresh() {
    if (dirty && !(await confirm({ title: t("taskWorkspace.discardTitle"), confirmLabel: t("taskWorkspace.discard"), cancelLabel: t("taskWorkspace.keepEditing"), tone: "warning" })).confirmed) return;
    setRefreshing(true); try { await reload(); clear(); mutation.reset(); } finally { setRefreshing(false); }
  }
  async function act(item: RecoveryRequest, type: "send" | "cancel") {
    const label = t(`recovery.${type}`);
    if (!(await confirm({ title: label, description: `${item.user_name} → ${item.new_email}. ${t("recovery.effects")}`, confirmLabel: label, tone: "warning" })).confirmed) return;
    mutation.mutate({ type, item });
  }
  const error = mutation.error ? normalizeAppError(mutation.error) : null;
  if (error?.category === "permission") return <PlatformLoadError error={mutation.error} message={t("platform.merchantDetail.error")} onRetry={() => void refresh()} />;
  const valid = Boolean(candidate && email && caseId && reason.trim() && mfa.trim() && (!candidate.identity_required || (reference.trim() && verified)));
  return <div className="space-y-4" data-testid="business-recovery">
    <div className="flex flex-wrap items-center justify-between gap-2"><h2 className="font-semibold">{t("recovery.title")}</h2><Button variant="secondary" disabled={pending} onClick={() => void refresh()}>{t("common.refresh")}</Button></div>
    <Card padding="md"><form className="space-y-4" data-testid="recovery-prepare" onSubmit={event => { event.preventDefault(); if (valid && !pending) mutation.mutate({ type: "prepare" }); }}>
      <fieldset disabled={pending} className="grid gap-4 sm:grid-cols-2">
        <Select label={t("recovery.account")} value={userId} required options={[{ value: "", label: t("common.select") }, ...data.candidates.map(row => ({ value: row.id, label: `${row.name} · ${row.email}` }))]} onChange={event => { setUserId(event.target.value); setVerified(false); setReference(""); }} />
        <Input name="new_email" label={t("recovery.newEmail")} type="email" required value={email} onChange={event => setEmail(event.target.value)} />
        <div className="space-y-2"><Input name="support_case_id" label={t("businessDetails.caseId")} required inputMode="numeric" pattern="[1-9][0-9]*" value={caseId} onChange={event => setCaseId(event.target.value)} />
          <Button type="button" variant="secondary" disabled={!candidate || pending} onClick={() => setCreatingCase(true)}>{t("supportCases.create")}</Button></div>
        <Textarea label={t("supportCases.reason")} required maxLength={2000} value={reason} onChange={event => setReason(event.target.value)} />
        {candidate?.identity_required && <div className="space-y-3 sm:col-span-2">
          <Textarea label={t("recovery.reference")} required maxLength={500} value={reference} onChange={event => setReference(event.target.value)} />
          <label className="flex items-start gap-2 text-sm"><input type="checkbox" className="mt-1" checked={verified} onChange={event => setVerified(event.target.checked)} />{t("recovery.attestation")}</label>
        </div>}
        {candidate && <div className="space-y-1 text-sm sm:col-span-2" role="status">
          <p>{t("recovery.mailChange")}: {t(`recovery.mail.${candidate.email_change_status}`)}</p>
          <p>{t("recovery.mfa")}: {t(candidate.mfa_enabled ? "recovery.enabled" : "recovery.notEnabled")}</p>
          {candidate.owner_required && <p>{t("recovery.waitingOwner")}</p>}
        </div>}
      </fieldset>
      {!data.candidates.length && <p role="status">{t("recovery.noCandidates")}</p>}
      <Input name="mfa" label={t("mfa.codeLabel")} autoComplete="one-time-code" disabled={pending} value={mfa} onChange={event => setMfa(event.target.value)} />
      <Button type="submit" disabled={!valid || pending} isLoading={mutation.isPending}>{t("recovery.prepare")}</Button>
    </form></Card>
    {error && (["mfa_code_invalid", "mfa_step_up_required"].includes(error.code) ? <p role="alert" className="text-platforma-danger">{t("businessDetails.mfaError")}</p> : <ErrorState error={mutation.error} />)}
    {error?.category === "conflict" && <p role="alert">{t("recovery.conflict")}</p>}
    {!data.requests.length && <p role="status" className="text-sm text-platforma-subtle">{t("recovery.empty")}</p>}
    {data.requests.map(item => <RecoverySummary key={item.id} item={item}>
      <Link className="platforma-focus-ring inline-flex min-h-10 items-center text-sm text-brand-700" to={`/platform/support/${item.support_case_id}`}>{t("businessDetails.caseId")} #{item.support_case_id}</Link>
      {["pending", "sent"].includes(item.status) && <div className="flex flex-wrap gap-2">
        <Button disabled={pending || !mfa.trim() || (item.owner_required && !item.owner_confirmed_at) || error?.category === "conflict"} onClick={() => void act(item, "send")}>{t(item.status === "sent" ? "recovery.resend" : "recovery.send")}</Button>
        <Button variant="secondary" disabled={pending || !mfa.trim()} onClick={() => void act(item, "cancel")}>{t("recovery.cancel")}</Button>
      </div>}
    </RecoverySummary>)}
    {creatingCase && candidate && <SupportCreateDialog scope={{ platform: true }} initialBusiness={Number(business)} fixedBusiness requester={{ id: candidate.id, name: `${candidate.name} · ${candidate.email}` }} onClose={() => setCreatingCase(false)} onCreated={item => { setCaseId(String(item.id)); setCreatingCase(false); }} />}
  </div>;
}

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router";
import { ownershipApi, type OwnershipSnapshot, type OwnershipTransfer } from "../../api/ownership";
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
import { OwnershipTransferSummary } from "../account/OwnershipTransferSummary";
import { PlatformLoadError } from "./PlatformData";

type Props = { business: string; onDraft: (value: { dirty: boolean; pending: boolean }) => void };
export function BusinessOwnershipPanel(props: Props) {
  const { t } = useI18n();
  const query = useQuery({ queryKey: ["platform-ownership", props.business], queryFn: () => ownershipApi.get(props.business), retry: false, gcTime: 0, refetchOnWindowFocus: false });
  if (query.isPending) return <LoadingState />;
  if (query.isError || !query.data) return <PlatformLoadError error={query.error} message={t("platform.merchantDetail.error")} onRetry={() => query.refetch()} />;
  return <OwnershipEditor {...props} data={query.data} reload={() => query.refetch()} />;
}

function OwnershipEditor({ business, data, onDraft, reload }: Props & { data: OwnershipSnapshot; reload: () => Promise<unknown> }) {
  const { t } = useI18n();
  const confirm = useActionConfirm();
  const queryClient = useQueryClient();
  const [recipient, setRecipient] = useState("");
  const [previousRole, setPreviousRole] = useState("");
  const [caseId, setCaseId] = useState("");
  const [reason, setReason] = useState("");
  const [mfa, setMfa] = useState("");
  const [reloading, setReloading] = useState(false);
  const hasPending = data.transfers.some(row => row.status === "pending");
  const dirty = Boolean(recipient || previousRole || caseId || reason || mfa);
  const mutation = useMutation({
    mutationFn: async (action: { type: "prepare" } | { type: "execute" | "cancel"; item: OwnershipTransfer }) => {
      const token = (await issueMfaStepUp(mfa)).step_up_token;
      return action.type === "prepare" ? ownershipApi.prepare(business, {
        new_owner_id: Number(recipient), expected_owner_id: data.owner.id,
        previous_owner_business_role_id: previousRole === "disabled" ? null : Number(previousRole),
        support_case_id: Number(caseId), reason,
      }, token) : ownershipApi.act(business, action.item.id, action.type, token);
    },
    retry: false,
    onSuccess: async () => {
      setRecipient(""); setPreviousRole(""); setCaseId(""); setReason(""); setMfa("");
      await reload();
      for (const key of ["platform-merchant", "platform-merchants", "platform-clinic-access"]) void queryClient.invalidateQueries({ queryKey: [key] });
    },
    onError: () => setMfa(""),
  });
  const pending = mutation.isPending || reloading;
  useEffect(() => { onDraft({ dirty, pending }); }, [dirty, pending, onDraft]);
  useEffect(() => () => onDraft({ dirty: false, pending: false }), [onDraft]);
  async function refresh() {
    if (dirty && !(await confirm({ title: t("taskWorkspace.discardTitle"), confirmLabel: t("taskWorkspace.discard"), cancelLabel: t("taskWorkspace.keepEditing"), tone: "warning" })).confirmed) return;
    setReloading(true);
    try { await reload(); setRecipient(""); setPreviousRole(""); setCaseId(""); setReason(""); setMfa(""); mutation.reset(); }
    finally { setReloading(false); }
  }
  async function act(item: OwnershipTransfer, type: "execute" | "cancel") {
    const label = t(type === "execute" ? "ownership.execute" : "ownership.cancel");
    if (!(await confirm({ title: label, description: `${item.previous_owner.name} → ${item.new_owner.name}. ${t("ownership.previousAccess")}: ${item.previous_owner_business_role?.name || t("ownership.disableAccess")}. ${t("ownership.sessionEffect")}`, confirmLabel: label, tone: "warning" })).confirmed) return;
    mutation.mutate({ type, item });
  }
  const error = mutation.error ? normalizeAppError(mutation.error) : null;
  if (error?.category === "permission") return <PlatformLoadError error={mutation.error} message={t("platform.merchantDetail.error")} onRetry={() => void refresh()} />;
  return <div data-testid="business-ownership" className="space-y-4">
    <div className="flex flex-wrap items-center justify-between gap-2"><h2 className="font-semibold">{t("ownership.title")}</h2><Button variant="secondary" disabled={pending} onClick={() => void refresh()}>{t("common.refresh")}</Button></div>
    {data.can_prepare && <Card padding="md"><form data-testid="ownership-prepare" className="space-y-4" onSubmit={event => { event.preventDefault(); if (!pending && !hasPending && recipient && previousRole && caseId && reason.trim() && mfa.trim()) mutation.mutate({ type: "prepare" }); }}>
      {!hasPending && <fieldset disabled={pending} className="grid gap-4 sm:grid-cols-2">
        <Select name="new_owner" label={t("ownership.newOwner")} value={recipient} required options={[{ value: "", label: t("common.select") }, ...data.candidates.map(person => ({ value: person.id, label: `${person.name} · ${person.email}` }))]} onChange={event => setRecipient(event.target.value)} />
        <Select name="previous_role" label={t("ownership.previousAccess")} value={previousRole} required options={[{ value: "", label: t("common.select") }, { value: "disabled", label: t("ownership.disableAccess") }, ...data.employee_roles.map(role => ({ value: role.id, label: role.name }))]} onChange={event => setPreviousRole(event.target.value)} />
        <Input name="support_case_id" label={t("businessDetails.caseId")} inputMode="numeric" pattern="[1-9][0-9]*" required value={caseId} onChange={event => setCaseId(event.target.value)} />
        <div className="sm:col-span-2"><Textarea label={t("supportCases.reason")} required maxLength={2000} value={reason} onChange={event => setReason(event.target.value)} /></div>
      </fieldset>}
      {!hasPending && !data.candidates.length && <p role="status" className="text-sm text-platforma-subtle">{t("ownership.noCandidates")}</p>}
      <Input name="mfa" label={t("mfa.codeLabel")} autoComplete="one-time-code" value={mfa} disabled={pending} onChange={event => setMfa(event.target.value)} />
      {!hasPending && <Button type="submit" isLoading={mutation.isPending} disabled={pending || !recipient || !previousRole || !caseId || !reason.trim() || !mfa.trim()}>{t("ownership.prepare")}</Button>}
      {hasPending && <p className="text-sm text-platforma-subtle">{t("ownership.confirmInAccount")}</p>}
    </form></Card>}
    {error && (["mfa_code_invalid", "mfa_step_up_required"].includes(error.code) ? <p role="alert" className="text-sm text-platforma-danger">{t("businessDetails.mfaError")}</p> : <ErrorState error={mutation.error} />)}
    {error?.category === "conflict" && <p role="alert" className="text-sm text-platforma-warning">{t("ownership.conflict")}</p>}
    {!data.transfers.length && <p className="text-sm text-platforma-subtle">{t("ownership.noRequests")}</p>}
    {data.transfers.map(item => <OwnershipTransferSummary key={item.id} item={item}>
      <Link className="platforma-focus-ring inline-flex min-h-10 items-center text-sm text-brand-700" to={`/platform/support/${item.support_case_id}`}>{t("businessDetails.caseId")} #{item.support_case_id}</Link>
      <div className="flex flex-wrap gap-2">
        {item.actions.execute && <Button disabled={pending || !mfa.trim() || error?.category === "conflict"} onClick={() => void act(item, "execute")}>{t("ownership.execute")}</Button>}
        {item.actions.cancel && <Button variant="secondary" disabled={pending || !mfa.trim()} onClick={() => void act(item, "cancel")}>{t("ownership.cancel")}</Button>}
      </div>
    </OwnershipTransferSummary>)}
  </div>;
}

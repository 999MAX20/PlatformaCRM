import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { billingCommerceApi, type BillingOrder, type PaymentAction, type PaymentCommand } from "../../api/billingCommerce";
import { issueMfaStepUp } from "../../api/auth";
import { normalizeAppError } from "../../api/appError";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { Textarea } from "../../components/ui/Textarea";
import { Card } from "../../components/ui/Card";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useActionConfirm } from "../../components/actions/ActionConfirmProvider";
import { useI18n } from "../../lib/i18n";
import { BillingOrderCard } from "../billing/BillingOrderCard";
import { SupportCreateDialog } from "../support/SupportCreateDialog";
import { ClinicPager } from "./ClinicReadUI";

export function BusinessBillingPanel({ business, onDraft }: { business: string; onDraft: (value: { dirty: boolean; pending: boolean }) => void }) {
  const { t } = useI18n(); const confirm = useActionConfirm();
  const [page, setPage] = useState(1); const [selected, setSelected] = useState<BillingOrder | null>(null);
  const [action, setAction] = useState<PaymentAction>("recover"); const [caseId, setCaseId] = useState("");
  const [reason, setReason] = useState(""); const [mfa, setMfa] = useState(""); const [reference, setReference] = useState("");
  const [amount, setAmount] = useState(""); const [currency, setCurrency] = useState(""); const [received, setReceived] = useState("");
  const [creatingCase, setCreatingCase] = useState(false);
  const query = useQuery({ queryKey: ["platform-billing-orders", business, page], queryFn: () => billingCommerceApi.get(business, true, page), retry: false, gcTime: 0, refetchOnWindowFocus: false });
  const clear = () => { setSelected(null); setCaseId(""); setReason(""); setMfa(""); setReference(""); setReceived(""); setAmount(""); setCurrency(""); };
  const mutation = useMutation({ mutationFn: async () => {
    const token = (await issueMfaStepUp(mfa)).step_up_token;
    const values: PaymentCommand = { support_case_id: Number(caseId), reason: reason.trim() };
    if (action === "confirm-bank") Object.assign(values, { reference: reference.trim(), amount, currency, received_at: new Date(received).toISOString() });
    return billingCommerceApi.action(business, selected!.id, action, values, token);
  }, retry: false, onSuccess: async () => { clear(); await query.refetch(); }, onError: () => setMfa("") });
  const dirty = Boolean(selected || caseId || reason || mfa || reference || received);
  const pending = query.isFetching || mutation.isPending;
  useEffect(() => { onDraft({ dirty, pending }); }, [dirty, pending, onDraft]);
  useEffect(() => () => onDraft({ dirty: false, pending: false }), [onDraft]);
  async function discard() {
    if (dirty && !(await confirm({ title: t("taskWorkspace.discardTitle"), confirmLabel: t("taskWorkspace.discard"), tone: "warning" })).confirmed) return false;
    clear(); return true;
  }
  async function select(order: BillingOrder) {
    if (selected?.id === order.id) return;
    if (!(await discard())) return;
    setSelected(order); setAmount(order.amount); setCurrency(order.currency); mutation.reset();
  }
  async function submit() {
    const title = t(`commerce.action.${action}`);
    if (!(await confirm({ title, description: `${selected?.plan} · ${amount || selected?.amount} ${currency || selected?.currency} · ${selected?.id}`, confirmLabel: title, tone: "warning" })).confirmed) return;
    mutation.mutate();
  }
  if (query.isLoading) return <LoadingState />;
  if (query.isError || !query.data) return <ErrorState error={query.error} action={<Button onClick={() => void query.refetch()}>{t("common.refresh")}</Button>} />;
  const data = query.data; const error = mutation.error ? normalizeAppError(mutation.error) : null;
  return <div className="space-y-4" data-testid="platform-billing">
    <Button variant="secondary" disabled={pending} onClick={() => void query.refetch()}>{t("common.refresh")}</Button>
    {!data.enabled && <p role="status">{t("commerce.unavailable")}</p>}
    {!data.commercial_expiry_enforced && <p role="status" className="text-sm">{t("commerce.rolloutPending")}</p>}
    {data.subscription && <Card padding="md"><h3 className="font-semibold">{t("commerce.currentSubscription")}: {data.subscription.plan}</h3>
      <p>{t(`commerce.subscription.${data.subscription.status}`)}</p>
      <details><summary className="platforma-focus-ring cursor-pointer py-2">{t("commerce.technicalLimits")}</summary>
        <ul className="space-y-1 text-sm">{data.subscription.technical_entitlements.map(row => <li key={row.metric}>{t(`commerce.metric.${row.metric}`)}: {row.value} / {row.limit ?? "—"}</li>)}</ul>
      </details></Card>}
    {!data.orders.length && <p role="status">{t("commerce.empty")}</p>}
    {data.orders.map(order => <BillingOrderCard key={order.id} order={order} platform>
      {data.enabled && <Button variant="secondary" disabled={pending} onClick={() => void select(order)}>{t("commerce.selectOrder")}</Button>}
    </BillingOrderCard>)}
    {selected && <Card padding="md"><form data-testid="billing-action" className="grid gap-3 sm:grid-cols-2" onSubmit={event => { event.preventDefault(); void submit(); }}>
      <h3 className="break-all font-semibold sm:col-span-2">{t("commerce.order")} {selected.id}</h3>
      <Select label={t("commerce.action")} value={action} disabled={pending} options={([...(data.can_confirm_bank ? ["confirm-bank"] : []), "recover", ...(selected.attempts.length && data.card_available ? ["reconcile"] : [])] as PaymentAction[]).map(value => ({ value, label: t(`commerce.action.${value}`) }))} onChange={event => setAction(event.target.value as PaymentAction)} />
      <Input label={t("businessDetails.caseId")} name="support_case_id" type="number" min="1" required value={caseId} disabled={pending} onChange={event => setCaseId(event.target.value)} />
      <Button type="button" variant="secondary" disabled={pending} onClick={() => setCreatingCase(true)}>{t("supportCases.create")}</Button>
      <Textarea label={t("supportCases.reason")} value={reason} required maxLength={2000} disabled={pending} onChange={event => setReason(event.target.value)} />
      {action === "confirm-bank" && <>
        <Input label={t("commerce.bankReference")} name="bank_reference" value={reference} required maxLength={128} disabled={pending} onChange={event => setReference(event.target.value)} />
        <Input label={t("commerce.receivedAt")} name="received_at" type="datetime-local" value={received} required disabled={pending} onChange={event => setReceived(event.target.value)} />
        <Input label={t("commerce.amount")} name="amount" value={amount} type="number" step="0.01" min="0.01" required disabled={pending} onChange={event => setAmount(event.target.value)} />
        <Input label={t("commerce.currency")} name="currency" value={currency} pattern="[A-Z]{3}" maxLength={3} required disabled={pending} onChange={event => setCurrency(event.target.value.toUpperCase())} />
      </>}
      <Input label={t("mfa.codeLabel")} name="mfa" value={mfa} required autoComplete="off" disabled={pending} onChange={event => setMfa(event.target.value)} />
      <div className="flex flex-wrap gap-2 sm:col-span-2"><Button type="submit" disabled={pending || !caseId || !reason.trim() || !mfa.trim()}>{t(`commerce.action.${action}`)}</Button>
        <Button type="button" variant="secondary" disabled={pending} onClick={() => void discard()}>{t("employeeAccess.clear")}</Button></div>
    </form></Card>}
    {error && (["mfa_code_invalid", "mfa_step_up_required"].includes(error.code) ? <p role="alert">{t("businessDetails.mfaError")}</p> : <ErrorState error={mutation.error} />)}
    {data.count > 10 && <ClinicPager page={page} size={10} count={data.count} change={value => { void discard().then(ok => { if (ok) setPage(value); }); }} />}
    {creatingCase && <SupportCreateDialog scope={{ platform: true }} initialBusiness={Number(business)} fixedBusiness onClose={() => setCreatingCase(false)} onCreated={item => { setCaseId(String(item.id)); setCreatingCase(false); }} />}
  </div>;
}

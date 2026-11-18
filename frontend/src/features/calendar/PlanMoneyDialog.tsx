import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { visitPlansApi, type VisitPlan, type PlanTermsDraft, type PlanTermsPreview } from "../../api/visitPlans";
import { normalizeAppError } from "../../api/appError";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { Select } from "../../components/ui/Select";
import { Textarea } from "../../components/ui/Textarea";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useActionConfirm } from "../../components/actions/ActionConfirmProvider";
import { useI18n } from "../../lib/i18n";
import { paymentSubmissionId } from "../payments/paymentSubmissionId";
import { usePaymentDraftGuard } from "../payments/usePaymentDraftGuard";

type Kind = "terms" | "remainder" | "credit";
export function PlanMoneyDialog({ plan, kind, onClose }: { plan: VisitPlan; kind: Kind; onClose: () => void }) {
  const { t } = useI18n();
  const cache = useQueryClient();
  const confirm = useActionConfirm();
  const terms = plan.money?.terms;
  const [revision, setRevision] = useState(plan.revision);
  const [mode, setMode] = useState<"package" | "per_visit">(terms?.mode || "per_visit");
  const [total, setTotal] = useState(terms?.total || "");
  const [bases, setBases] = useState<Record<number, string>>(() => Object.fromEntries(plan.steps.filter(s => !s.removed_at).map(s => [s.id, terms?.lines.find(l => l.step === s.id)?.base || ""])));
  const [reason, setReason] = useState("");
  const [consent, setConsent] = useState(false);
  const [receipt, setReceipt] = useState("");
  const [amount, setAmount] = useState("");
  const [choice, setChoice] = useState("");
  const [creditPage, setCreditPage] = useState(1);
  const credits = useQuery({ queryKey: ["visit-plans", "credit-options", plan.business, plan.id, creditPage],
    queryFn: () => visitPlansApi.creditOptions(plan.business, plan.id, creditPage), enabled: kind === "credit" });
  const selectedCredit = credits.data?.results.find(item => `${item.source_plan}:${item.receipt}` === receipt);
  const [preview, setPreview] = useState<PlanTermsPreview>();
  const [dirty, setDirty] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [localError, setLocalError] = useState("");
  const attempt = useRef<{ key: string; payload: Record<string, unknown> } | null>(null);
  const submitting = useRef(false);
  const termsDraft = (): PlanTermsDraft => ({ expected_revision: revision, mode, total: total.replace(",", ".") || "0",
    base_prices: plan.steps.filter(s => !s.removed_at).map(s => ({ step: s.id, amount: (bases[s.id] || "").replace(",", ".") })), reason, consent });
  const calculation = useMutation({ mutationFn: () => visitPlansApi.previewTerms(plan.business, plan.id, termsDraft()), onSuccess: setPreview });
  const save = useMutation({
    onSettled: () => { submitting.current = false; },
    mutationFn: () => visitPlansApi.command(plan.business, plan.id, kind === "terms" ? "accept-terms" : kind === "credit" ? "use-credit" : "settle-remainder", attempt.current!.payload, attempt.current!.key),
    onSuccess: async () => {
      await Promise.all([cache.invalidateQueries({ queryKey: ["visit-plans"] }), cache.invalidateQueries({ queryKey: ["client-payments"] })]);
      onClose();
    },
    onError: error => {
      const normalized = normalizeAppError(error);
      const status = normalized.status;
      const unknownResult = !status || status >= 500 || normalized.code === "idempotency_conflict";
      setUncertain(unknownResult);
      if (!unknownResult) attempt.current = null;
    },
  });
  const pending = save.isPending || calculation.isPending;
  const stale = !uncertain && normalizeAppError(save.error || calculation.error).status === 409;
  usePaymentDraftGuard(dirty, pending, uncertain);
  async function close() {
    if (pending) return;
    if (dirty || uncertain) {
      const answer = await confirm({ title: t("payments.discardTitle"), description: t(uncertain ? "payments.uncertainClose" : "payments.discardText"), confirmLabel: t("payments.discard"), tone: "warning" });
      if (!answer.confirmed) return;
    }
    onClose();
  }
  async function refresh() {
    try {
      const current = await visitPlansApi.get(plan.business, plan.id);
      setRevision(current.revision); setPreview(undefined); setConsent(false); attempt.current = null;
      save.reset(); calculation.reset();
      await cache.invalidateQueries({ queryKey: ["visit-plans"] });
    } catch { setLocalError(t("planMoney.refreshFailed")); }
  }
  function changed() { setDirty(true); setPreview(undefined); calculation.reset(); setConsent(false); setLocalError(""); }
  function submit(event: React.FormEvent) {
    event.preventDefault();
    if (submitting.current || pending || stale) return;
    if (uncertain && attempt.current) { submitting.current = true; save.mutate(); return; }
    if (kind === "terms" && !preview) {
      if (mode === "package" && Number(total.replace(",", ".")) > 0 && Object.values(bases).every(value => Number(value.replace(",", ".")) === 0)) {
        setLocalError(t("planMoney.zeroBases")); return;
      }
      calculation.mutate(); return;
    }
    if (!consent || !reason.trim()) { setLocalError(t("planMoney.consentRequired")); return; }
    const payload = kind === "terms" ? { ...termsDraft(), preview_hash: preview!.preview_hash }
      : kind === "credit" ? { expected_revision: revision, ...selectedCredit, amount: amount.replace(",", "."), reason, consent }
      : { expected_revision: revision, receipt: Number(receipt), amount: amount.replace(",", "."), choice, reason, consent };
    attempt.current = { key: paymentSubmissionId(), payload };
    submitting.current = true;
    save.mutate();
  }
  const issue = save.error || calculation.error;
  return <Modal open title={t(kind === "terms" ? "planMoney.terms" : kind === "credit" ? "planMoney.useCredit" : "planMoney.remainder")} onClose={() => void close()} size="lg" closeOnBackdrop={false}>
    <form onSubmit={submit} className="space-y-4">
      <p className="font-semibold">{plan.client_name} · {t("plans.plan")} #{plan.id}</p>
      {issue && <ErrorState error={issue} message={t(stale ? "planMoney.stale" : normalizeAppError(issue).fieldErrors.legacy_payments ? "planMoney.legacyPayments" : "planMoney.invalid")} />}
      {localError && <p role="alert" className="text-platforma-danger">{localError}</p>}
      {uncertain && <p role="alert">{t("payments.uncertain")}</p>}
      {stale && <Button type="button" variant="secondary" onClick={() => void refresh()}>{t("planMoney.refresh")}</Button>}
      <fieldset disabled={pending || uncertain || stale} className="space-y-4">
        {kind === "terms" ? <>
          <Select label={t("planMoney.mode")} value={mode} onChange={e => { setMode(e.target.value as typeof mode); changed(); }} options={[{ value: "per_visit", label: t("planMoney.perVisit") }, { value: "package", label: t("planMoney.package") }]} />
          {mode === "package" && <Input label={t("planMoney.total")} value={total} inputMode="decimal" required onChange={e => { setTotal(e.target.value); changed(); }} />}
          <div className="grid gap-3 sm:grid-cols-2">{plan.steps.filter(s => !s.removed_at).map(step => <Input key={step.id} label={`${step.service_name} · ${t("planMoney.base")}`} value={bases[step.id] || ""} inputMode="decimal" required readOnly={step.status === "completed" && !!terms} onChange={e => { setBases(current => ({ ...current, [step.id]: e.target.value })); changed(); }} />)}</div>
          {preview && <section className="space-y-2 border-t border-platforma-border pt-3" aria-live="polite"><h3 className="font-semibold">{t("planMoney.preview")}: {preview.total} {preview.currency}</h3>
            {preview.lines.map(line => <p key={line.step} className="flex flex-wrap justify-between gap-2 text-sm"><span>{plan.steps.find(s => s.id === line.step)?.service_name}</span><span>{line.amount} {preview.currency}</span></p>)}
            <p className="text-sm text-platforma-subtle">{t("planMoney.frozenNotice")}</p>
            <dl className="grid gap-2 sm:grid-cols-2">{Object.entries(preview.balance).map(([key, value]) => <div key={key}><dt className="text-sm">{t(`planMoney.${key === "unallocated" ? "advance" : key}`)}</dt><dd className="tabular-nums">{value} {preview.currency}</dd></div>)}</dl>
          </section>}
        </> : kind === "credit" ? <>
          {credits.isPending ? <LoadingState /> : credits.error ? <ErrorState error={credits.error} action={<Button type="button" onClick={() => void credits.refetch()}>{t("common.retry")}</Button>} /> : <>
            <Select label={t("planMoney.source")} required value={receipt} options={[{ value: "", label: t("planMoney.selectSource") }, ...(credits.data?.results || []).map(item => ({ value: `${item.source_plan}:${item.receipt}`, label: `${t("plans.plan")} #${item.source_plan} · ${item.amount} ${item.currency}` }))]} onChange={e => { setReceipt(e.target.value); setDirty(true); setConsent(false); }} />
            {!credits.data?.results.length && <p>{t("planMoney.noCredit")}</p>}
            <div className="flex justify-between gap-2"><Button type="button" variant="secondary" disabled={!credits.data?.previous} onClick={() => { setCreditPage(p => p - 1); setReceipt(""); }}>{t("pagination.previous")}</Button><Button type="button" variant="secondary" disabled={!credits.data?.next} onClick={() => { setCreditPage(p => p + 1); setReceipt(""); }}>{t("pagination.next")}</Button></div>
          </>}
          <Input label={t("payments.amount")} inputMode="decimal" value={amount} required onChange={e => { setAmount(e.target.value); setDirty(true); setConsent(false); }} />
        </> : <>
          <Select label={t("planMoney.source")} value={receipt} required options={[{ value: "", label: t("planMoney.selectSource") }, ...(plan.money?.sources || []).filter(s => Number(s.available) > 0).map(s => ({ value: s.id, label: `#${s.id} · ${s.available} ${terms?.currency || ""}` }))]} onChange={e => { setReceipt(e.target.value); setDirty(true); setConsent(false); }} />
          <Input label={t("payments.amount")} inputMode="decimal" value={amount} required onChange={e => { setAmount(e.target.value); setDirty(true); setConsent(false); }} />
          <Select label={t("planMoney.choice")} value={choice} required options={[{ value: "", label: t("planMoney.choose") }, { value: "refund", label: t("payments.refund") }, { value: "retain", label: t("planMoney.retain") }]} onChange={e => { setChoice(e.target.value); setDirty(true); setConsent(false); }} />
          <p className="text-sm text-platforma-subtle">{t("payments.manualNotice")}</p>
        </>}
        {(kind !== "terms" || preview) && <>
          <Textarea label={t("plans.reason")} value={reason} maxLength={500} required onChange={e => { setReason(e.target.value); setDirty(true); }} />
          <label className="flex min-h-11 cursor-pointer items-center gap-3 text-sm"><input type="checkbox" required checked={consent} onChange={e => { setConsent(e.target.checked); setDirty(true); }} />{t("planMoney.consent")}</label>
        </>}
      </fieldset>
      <div className="flex flex-wrap justify-end gap-2"><Button type="button" variant="secondary" disabled={pending} onClick={() => void close()}>{t("common.cancel")}</Button>
        <Button type="submit" disabled={stale || !uncertain && kind === "credit" && !selectedCredit} isLoading={pending}>{t(uncertain ? "common.retry" : kind === "terms" && !preview ? "planMoney.calculate" : "plans.confirm")}</Button></div>
    </form>
  </Modal>;
}

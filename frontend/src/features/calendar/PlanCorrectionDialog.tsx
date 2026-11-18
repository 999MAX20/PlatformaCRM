import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { normalizeAppError } from "../../api/appError";
import { visitPlansApi, type PlanCorrectionKind, type PlanCorrectionPreview, type PlanStep, type VisitPlan } from "../../api/visitPlans";
import { useActionConfirm } from "../../components/actions/ActionConfirmProvider";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { Select } from "../../components/ui/Select";
import { Textarea } from "../../components/ui/Textarea";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { refreshAppointmentQueries } from "../../lib/appointmentCache";
import { useI18n } from "../../lib/i18n";
import { paymentSubmissionId } from "../payments/paymentSubmissionId";
import { usePaymentDraftGuard } from "../payments/usePaymentDraftGuard";

export function PlanCorrectionDialog({ plan, kind, step, onClose }: {
  plan: VisitPlan; kind: PlanCorrectionKind; step?: PlanStep; onClose: () => void;
}) {
  const { t, language } = useI18n();
  const cache = useQueryClient();
  const confirm = useActionConfirm();
  const [revision, setRevision] = useState(plan.revision);
  const [receipt, setReceipt] = useState("");
  const [page, setPage] = useState(1);
  const [reason, setReason] = useState("");
  const [consent, setConsent] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [localError, setLocalError] = useState("");
  const [preview, setPreview] = useState<PlanCorrectionPreview>();
  const attempt = useRef<{ key: string; payload: Record<string, unknown> } | null>(null);
  const submitting = useRef(false);
  const replacement = kind === "create-replacement";
  const attach = kind === "attach-legacy";
  const options = useQuery({ queryKey: ["visit-plans", "legacy-options", plan.business, plan.id, page],
    queryFn: () => visitPlansApi.legacyOptions(plan.business, plan.id, page), enabled: attach });
  const draft = () => ({ expected_revision: revision, ...(attach ? { receipt: Number(receipt) } : { step_id: step!.id }) });
  const calculation = useMutation({ mutationFn: () => visitPlansApi.previewCorrection(plan.business, plan.id,
    kind as Exclude<PlanCorrectionKind, "create-replacement">, draft()), onSuccess: value => { setPreview(value); setConsent(false); } });
  const save = useMutation({
    mutationFn: () => visitPlansApi.command(plan.business, plan.id, kind, attempt.current!.payload, attempt.current!.key),
    onSettled: () => { submitting.current = false; },
    onSuccess: async () => {
      await Promise.all([refreshAppointmentQueries(cache), ...["client-payments", "payments", "analytics"].map(key => cache.invalidateQueries({ queryKey: [key] }))]);
      onClose();
    },
    onError: error => {
      const issue = normalizeAppError(error);
      const unknown = !issue.status || issue.status >= 500 || issue.code === "idempotency_conflict";
      setUncertain(unknown);
      if (!unknown) attempt.current = null;
    },
  });
  const pending = calculation.isPending || save.isPending;
  const issue = save.error || calculation.error;
  const stale = !uncertain && normalizeAppError(issue).status === 409;
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
      save.reset(); calculation.reset(); setLocalError("");
      await cache.invalidateQueries({ queryKey: ["visit-plans"] });
    } catch { setLocalError(t("planMoney.refreshFailed")); }
  }
  function select(value: string) {
    setReceipt(value); setPreview(undefined); setConsent(false); setDirty(true); calculation.reset(); save.reset();
  }
  function submit(event: React.FormEvent) {
    event.preventDefault();
    if (pending || submitting.current || stale) return;
    if (uncertain && attempt.current) { submitting.current = true; save.mutate(); return; }
    if (!replacement && !preview) { calculation.mutate(); return; }
    if (!consent || !reason.trim()) { setLocalError(t("planCorrection.required")); return; }
    attempt.current = { key: paymentSubmissionId(), payload: { ...draft(), reason, consent, ...(preview ? { preview_hash: preview.preview_hash } : {}) } };
    submitting.current = true; save.mutate();
  }
  const money = (value: string | number) => new Intl.NumberFormat(language === "kk" ? "kk-KZ" : language === "en" ? "en-US" : "ru-RU", { style: "currency", currency: preview?.currency || plan.money?.terms?.currency || "KZT" }).format(Number(value));
  const pairs = attach ? [["planMoney.remaining", "remaining"]] : [["planMoney.total", "total"], ["planMoney.allocated", "allocated"], ["planMoney.retained", "retained"]];
  return <Modal open title={t(replacement ? "planCorrection.create-replacement" : `planCorrection.title.${kind}`)} onClose={() => void close()} closeOnBackdrop={false} size="lg">
    <form className="space-y-4" onSubmit={submit}>
      <div><p className="font-semibold">{plan.client_name} · {t("plans.plan")} #{plan.id}</p>{step && <p className="mt-1 text-sm">{step.service_name} · {t("plans.step")} #{step.id}</p>}</div>
      <p className="text-sm text-platforma-subtle">{t(`planCorrection.notice.${kind}`)}</p>
      {issue && <ErrorState error={issue} message={t(stale ? "planMoney.stale" : "planCorrection.invalid")} />}
      {localError && <p role="alert" className="text-platforma-danger">{localError}</p>}
      {uncertain && <p role="alert">{t("payments.uncertain")}</p>}
      {stale && <Button type="button" variant="secondary" onClick={() => void refresh()}>{t("planMoney.refresh")}</Button>}
      <fieldset disabled={pending || uncertain || stale} className="min-w-0 space-y-4">
        {attach && (options.isPending ? <LoadingState /> : options.error ? <ErrorState error={options.error} action={<Button type="button" onClick={() => void options.refetch()}>{t("common.retry")}</Button>} /> : <>
          <Select label={t("planMoney.source")} required value={receipt} onChange={e => select(e.target.value)} options={[{ value: "", label: t("planMoney.selectSource") }, ...(options.data?.results || []).map(item => ({ value: item.id, label: `#${item.id} · ${new Date(item.occurred_at).toLocaleDateString(language)} · ${item.available} ${item.currency} · ${t(`payments.method.${item.method}`)}` }))]} />
          {!options.data?.results.length && <p role="status">{t("planCorrection.noLegacy")}</p>}
          {(options.data?.previous || options.data?.next) && <div className="flex justify-between gap-2"><Button type="button" variant="secondary" disabled={!options.data.previous} onClick={() => { setPage(p => p - 1); select(""); }}>{t("pagination.previous")}</Button><Button type="button" variant="secondary" disabled={!options.data.next} onClick={() => { setPage(p => p + 1); select(""); }}>{t("pagination.next")}</Button></div>}
        </>)}
        {preview && <section aria-live="polite" className="space-y-4 border-y border-platforma-border py-4">
          {attach && <dl className="grid gap-3 sm:grid-cols-3">{[["payments.amount", "original_amount"], ["planMoney.refunded", "refunded_before"], ["planCorrection.attached", "amount"]].map(([label, key]) => <div key={key}><dt className="text-sm text-platforma-subtle">{t(label)}</dt><dd className="break-words font-semibold tabular-nums">{money(preview[key])}</dd></div>)}</dl>}
          <div className="grid grid-cols-2 gap-x-3 gap-y-3 text-sm sm:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)_minmax(0,1fr)]">
            <span className="hidden sm:block" /><span className="text-platforma-subtle">{t("planCorrection.before")}</span><span className="font-semibold">{t("planCorrection.after")}</span>
            {pairs.map(([label, key]) => <div key={key} className="contents"><span className="col-span-2 border-t border-platforma-border pt-2 sm:col-span-1 sm:border-0 sm:pt-0">{t(label)}</span><span className="tabular-nums">{money(preview[`${key}_before`])}</span><span className="font-semibold tabular-nums">{money(preview[`${key}_after`])}</span></div>)}
          </div>
        </section>}
        {(preview || replacement) && <>
          <Textarea label={t("plans.reason")} required maxLength={500} value={reason} onChange={e => { setReason(e.target.value); setDirty(true); setLocalError(""); }} />
          <label className="flex min-h-11 cursor-pointer items-start gap-3 py-2 text-sm"><input className="mt-1 shrink-0" type="checkbox" required checked={consent} onChange={e => { setConsent(e.target.checked); setDirty(true); }} />{t(`planCorrection.consent.${kind}`)}</label>
        </>}
      </fieldset>
      <div className="flex flex-wrap justify-end gap-2"><Button type="button" variant="secondary" disabled={pending} onClick={() => void close()}>{t("common.cancel")}</Button><Button type="submit" variant={kind === "annul-completion" && preview ? "warning" : "primary"} isLoading={pending} disabled={stale || !uncertain && attach && (!receipt || options.isPending || !!options.error)}>{t(uncertain ? "common.retry" : !replacement && !preview ? "planMoney.calculate" : `planCorrection.${kind}`)}</Button></div>
    </form>
  </Modal>;
}

export function PlanStepCorrection({ plan, step }: { plan: VisitPlan; step: PlanStep }) {
  const { t } = useI18n();
  const [kind, setKind] = useState<PlanCorrectionKind>();
  const allowed = plan.money?.can_correct && !plan.is_archived;
  if (!step.completion_corrected && !step.replaces_step && !(allowed && step.status === "completed" && !step.removed_at && plan.money?.terms_current)) return null;
  return <div className="mt-2 space-y-2">
    {step.completion_corrected && <p className="text-sm">{t("planCorrection.corrected")}{step.replacement_step ? ` · ${t("planCorrection.replacementStep")} #${step.replacement_step}` : ""}</p>}
    {step.replaces_step && <p className="text-sm">{t("planCorrection.replacesStep")} #{step.replaces_step}</p>}
    {allowed && (step.completion_corrected && !step.replacement_step ? <Button variant="secondary" onClick={() => setKind("create-replacement")}>{t("planCorrection.create-replacement")}</Button> : step.status === "completed" && !step.removed_at && plan.money?.terms_current ? <Button variant="secondary" onClick={() => setKind("annul-completion")}>{t("planCorrection.annul-completion")}</Button> : null)}
    {kind && <PlanCorrectionDialog plan={plan} step={step} kind={kind} onClose={() => setKind(undefined)} />}
  </div>;
}

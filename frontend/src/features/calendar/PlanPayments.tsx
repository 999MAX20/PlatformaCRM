import { useState } from "react";
import type { VisitPlan } from "../../api/visitPlans";
import { Button } from "../../components/ui/Button";
import { useI18n } from "../../lib/i18n";
import { PaymentForm } from "../payments/PaymentForm";
import { PlanMoneyDialog } from "./PlanMoneyDialog";
import { PlanTermsHistory } from "./PlanTermsHistory";

export function PlanPayments({ plan, currency }: { plan: VisitPlan; currency: string }) {
  const { t, language } = useI18n();
  const [dialog, setDialog] = useState<"payment" | "terms" | "remainder" | "credit" | null>(null);
  const funds = plan.money;
  if (!funds) return null;
  const terms = funds.terms;
  const unit = terms?.currency || currency;
  const formatted = (value: string) => new Intl.NumberFormat(language === "kk" ? "kk-KZ" : language === "en" ? "en-US" : "ru-RU", { style: "currency", currency: unit }).format(Number(value));
  const metrics = [
    ["planMoney.total", terms?.total], ["planMoney.received", funds.received],
    ["planMoney.allocated", funds.allocated], ["planMoney.advance", funds.unallocated], ["planMoney.remaining", funds.remaining],
  ];
  return <section className="space-y-4 rounded-card border border-platforma-border bg-surface-card p-4" aria-label={t("planMoney.terms")} data-testid="plan-payments">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div><h3 className="font-semibold">{terms ? t(terms.mode === "package" ? "planMoney.package" : "planMoney.perVisit") : t("planMoney.notAgreed")}</h3>
        {terms && !funds.terms_current && <p role="status" className="mt-1 text-sm text-platforma-warning">{t("planMoney.reviewComposition")}</p>}</div>
      <div className="flex flex-wrap gap-2">
        {funds.can_receive && !plan.is_archived && <Button variant="secondary" onClick={() => setDialog("terms")}>{t(terms ? "planMoney.changeTerms" : "planMoney.acceptTerms")}</Button>}
        {funds.can_receive && funds.terms_current && !plan.is_archived && <Button onClick={() => setDialog("payment")}>{t("payments.add")}</Button>}
      </div>
    </div>
    {terms && <dl className="grid grid-cols-1 gap-4 min-[400px]:grid-cols-2 md:grid-cols-3 xl:grid-cols-5">{metrics.map(([label, value]) => <div key={label} className="min-w-0"><dt className="text-sm text-platforma-subtle">{t(label!)}</dt><dd className="mt-1 break-words text-lg font-semibold tabular-nums">{formatted(value || "0")}</dd></div>)}</dl>}
    {(Number(funds.refunded) > 0 || Number(funds.retained) > 0 || Number(funds.incoming_credit) > 0 || Number(funds.outgoing_credit) > 0) && <dl className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
      {[["planMoney.refunded", funds.refunded], ["planMoney.retained", funds.retained], ["planMoney.incoming", funds.incoming_credit], ["planMoney.outgoing", funds.outgoing_credit]].filter(([, value]) => Number(value) > 0).map(([label, value]) => <div key={label}><dt>{t(label)}</dt><dd className="font-semibold tabular-nums">{formatted(value)}</dd></div>)}
    </dl>}
    {(funds.can_manage && Number(funds.unallocated) > 0 || funds.can_receive && funds.terms_current) && !plan.is_archived && <div className="flex flex-wrap gap-2">
      {funds.can_manage && Number(funds.unallocated) > 0 && <Button variant="secondary" onClick={() => setDialog("remainder")}>{t("planMoney.remainder")}</Button>}
      {funds.can_receive && funds.terms_current && <Button variant="secondary" onClick={() => setDialog("credit")}>{t("planMoney.useCredit")}</Button>}
    </div>}
    {funds.sources.length > 0 && <details className="border-t border-platforma-border pt-3"><summary className="platforma-focus-ring cursor-pointer rounded py-2 font-semibold">{t("planMoney.sources")}</summary><ul className="divide-y divide-platforma-border">
      {funds.sources.map(source => <li key={source.id} className="flex flex-wrap justify-between gap-2 py-3 text-sm"><span>#{source.id} · {new Date(source.occurred_at).toLocaleDateString(language)} · {t(`payments.method.${source.method}`)}</span><span>{formatted(source.amount)} · {t("planMoney.available")}: {formatted(source.available)}</span></li>)}
    </ul></details>}
    {dialog === "payment" && <PaymentForm businessId={plan.business} currency={unit} initialClient={{ id: plan.client, label: plan.client_name }} plan={{ id: plan.id, revision: plan.revision, total: terms!.total, remaining: funds.remaining,
      appointments: plan.steps.filter(step => step.appointment && !step.removed_at).map(step => ({ id: step.appointment!, label: `${step.service_name} · #${step.appointment}` })) }} canLinkDeal={false} canLinkAppointment onClose={() => setDialog(null)} onSaved={() => setDialog(null)} />}
    {terms && <PlanTermsHistory business={plan.business} plan={plan.id} />}
    {dialog && dialog !== "payment" && <PlanMoneyDialog plan={plan} kind={dialog} onClose={() => setDialog(null)} />}
  </section>;
}

export function PlanStepMoney({ plan, stepId }: { plan: VisitPlan; stepId: number }) {
  const { t } = useI18n();
  const line = plan.money?.terms?.lines.find(item => item.step === stepId);
  const step = plan.steps.find(item => item.id === stepId);
  if (!line || !step) return null;
  const allocated = plan.money!.allocations.filter(item => item.appointment === step.appointment)
    .reduce((sum, item) => sum + (item.reversal_of ? -1 : 1) * Math.round(Number(item.amount) * 100), 0);
  return <p className="mt-2 text-sm tabular-nums">{t("planMoney.visitPrice")}: {line.amount} {plan.money!.terms!.currency}
    {step.status === "completed" && <> · {t("planMoney.allocated")}: {(allocated / 100).toFixed(2)} {plan.money!.terms!.currency}</>}</p>;
}

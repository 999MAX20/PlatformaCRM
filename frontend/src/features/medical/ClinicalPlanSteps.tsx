import { useId, useLayoutEffect, useRef } from "react";
import type { ClinicalContent, ClinicalPlanAccess } from "../../api/medicalClinical";
import { Button } from "../../components/ui/Button";
import { Textarea } from "../../components/ui/Textarea";
import { useI18n } from "../../lib/i18n";
import { ClinicalPlanVisitLink, ClinicalVisitStepLabel } from "./ClinicalPlanVisitLink";
import { ClinicalPlanTeeth } from "./ClinicalPlanTeeth";

export function ClinicalPlanSteps({ content, onChange, disabled, readOnly, planAccess }: {
  content: ClinicalContent; onChange: (value: ClinicalContent) => void; disabled: boolean; readOnly: boolean;
  planAccess?: ClinicalPlanAccess;
}) {
  const { t } = useI18n();
  const prefix = useId();
  const focus = useRef<string | null>(null);
  const steps = content.plan_steps ?? [];
  const blocked = disabled || readOnly;
  useLayoutEffect(() => {
    if (focus.current) { document.getElementById(focus.current)?.focus(); focus.current = null; }
  }, [content]);
  function move(index: number, offset: number) {
    const next = [...steps];
    [next[index], next[index + offset]] = [next[index + offset], next[index]];
    focus.current = `${prefix}-${steps[index].id}`;
    onChange({ ...content, plan_steps: next });
  }
  return <section className="space-y-3" data-testid="clinical-plan-steps">
    <h3 className="text-sm font-semibold">{t("medical.plan.steps")}</h3>
    {!steps.length ? <p className="text-sm text-platforma-subtle">{t("medical.clinical.notRecorded")}</p> : null}
    <ol className="space-y-4">
      {steps.map((step, index) => <li key={step.id} className="space-y-2">
        <Textarea id={`${prefix}-${step.id}`} label={t("medical.plan.step", { number: index + 1 })}
          value={step.description} maxLength={4000} disabled={disabled} readOnly={readOnly}
          onChange={event => onChange({ ...content, plan_steps: steps.map(item => item.id === step.id
            ? { ...item, description: event.target.value } : item) })} />
        <ClinicalPlanTeeth value={step.teeth} disabled={disabled} readOnly={readOnly} onChange={teeth =>
          onChange({ ...content, plan_steps: steps.map(item => item.id === step.id ? { ...item, teeth } : item) })} />
        <ClinicalPlanVisitLink value={step.visit_step} access={planAccess} disabled={disabled} readOnly={readOnly}
          onChange={value => onChange({ ...content, plan_steps: steps.map(item => {
            if (item.id !== step.id) return item;
            const next = { ...item }; if (value) next.visit_step = value; else delete next.visit_step;
            return next;
          }) })} />
        {!readOnly ? <div className="flex flex-wrap gap-2">
          <Button type="button" variant="secondary" size="lg" disabled={blocked || index === 0}
            aria-label={t("medical.plan.moveUpStep", { number: index + 1 })} onClick={() => move(index, -1)}>{t("medical.plan.moveUp")}</Button>
          <Button type="button" variant="secondary" size="lg" disabled={blocked || index === steps.length - 1}
            aria-label={t("medical.plan.moveDownStep", { number: index + 1 })} onClick={() => move(index, 1)}>{t("medical.plan.moveDown")}</Button>
          <Button type="button" variant="ghost" size="lg" disabled={blocked}
            aria-label={t("medical.plan.removeStep", { number: index + 1 })} onClick={() => {
              if (!window.confirm(t("medical.plan.confirmRemove"))) return;
              const next = steps.filter(item => item.id !== step.id);
              const neighbor = next[Math.min(index, next.length - 1)];
              focus.current = neighbor ? `${prefix}-${neighbor.id}` : `${prefix}-add`;
              onChange({ ...content, plan_steps: next });
            }}>{t("medical.plan.remove")}</Button>
        </div> : null}
      </li>)}
    </ol>
    {!readOnly ? <Button id={`${prefix}-add`} type="button" size="lg" variant="secondary" disabled={blocked || steps.length >= 100}
      onClick={() => {
        const id = crypto.randomUUID(); focus.current = `${prefix}-${id}`;
        onChange({ ...content, plan_steps: [...steps, { id, description: "" }] });
      }}>{t("medical.plan.addStep")}</Button> : null}
  </section>;
}

export function ClinicalPlanStepsRead({ content }: { content: ClinicalContent }) {
  const { t } = useI18n();
  if (!content.plan_steps?.length) return null;
  return <div className="space-y-2" data-testid="clinical-plan-history">
    <h3 className="text-sm font-semibold text-platforma-subtle">{t("medical.plan.steps")}</h3>
    <ol className="list-decimal space-y-2 pl-5">
      {content.plan_steps.map(step => <li key={step.id} className="whitespace-pre-wrap break-words text-sm">
        {step.description || t("medical.clinical.notRecorded")}
        <ClinicalPlanTeeth value={step.teeth} disabled={false} readOnly onChange={() => {}} />
        {step.visit_step ? <ClinicalVisitStepLabel step={step.visit_step} /> : null}
      </li>)}
    </ol>
  </div>;
}

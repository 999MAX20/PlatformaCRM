import type { ReactNode } from "react";
import { Link } from "react-router";
import { ArrowRight, BookOpen, CheckCircle2, Circle, Plus, Radio, Sparkles } from "lucide-react";

import { Button } from "../../../components/ui/Button";
import { useI18n } from "../../../lib/i18n";
import { cn } from "../../../lib/cn";
import type { OnboardingStep } from "../aiAgentsTypes";
export function EmptyAgentsState({ canManage, onCreate }: { canManage: boolean; onCreate: () => void }) {
  const { t } = useI18n();
  return (
    <section className="flex min-w-0 flex-col items-center justify-center py-10 text-center sm:py-16" data-testid="empty-agents-state">
        <h2 className="text-2xl font-black text-midnight">{t("aiAgents.emptyAgentsTitle")}</h2>
        <p className="mt-2 max-w-xl text-sm font-semibold leading-6 text-platforma-faint">
          {t("aiAgents.emptyAgentsText")}
        </p>
        {canManage ? (
          <Button className="mt-5" type="button" data-focus-return-id="ai-agent-create" onClick={onCreate}>
            <Plus aria-hidden="true" size={16} />
            {t("aiAgents.createAgent")}
          </Button>
        ) : null}
    </section>
  );
}

export function HelpCard({ title, text, recommendation }: { title: string; text: string; recommendation: string }) {
  return (
    <div className="rounded-2xl border border-ai-100 bg-ai-50 p-4">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-white text-ai-700">
          <Sparkles size={18} />
        </div>
        <div>
          <h3 className="font-black text-midnight">{title}</h3>
          <p className="mt-1 text-sm font-semibold leading-6 text-platforma-subtle">{text}</p>
          <p className="mt-2 text-sm font-black leading-6 text-ai-700">{recommendation}</p>
        </div>
      </div>
    </div>
  );
}

export function FieldHint({ children }: { children: ReactNode }) {
  return <p className="mt-2 text-xs font-semibold leading-5 text-platforma-faint">{children}</p>;
}

export function OnboardingProgress({ steps }: { steps: OnboardingStep[] }) {
  const { t } = useI18n();
  const icons = [null, BookOpen, Radio];
  const complete = steps.every(step => step.done);
  return (
    <section className="space-y-4">
      <div>
        <h3 className="text-base font-semibold text-platforma-ink">{t("aiAgents.preparation.title")}</h3>
        <p className="mt-1 text-sm leading-6 text-platforma-subtle">{t(complete ? "aiAgents.preparation.allComplete" : "aiAgents.preparation.requiredSteps")}</p>
      </div>
      <nav aria-label={t("aiAgents.firstLaunchTitle")} className="grid gap-3 sm:grid-cols-3">
      {steps.map((step, index) => {
        const Icon = icons[index];
        return <Link key={step.href} to={step.href} className={cn(
          "platforma-focus-ring flex min-w-0 flex-col gap-3 rounded-xl border p-4 transition-colors hover:border-brand-800",
          step.done ? "border-platforma-success/30 bg-[var(--platforma-success-soft)]" : "border-brand-700 bg-white hover:bg-brand-50",
        )}>
          <span className={cn("flex items-center gap-2 text-xs font-semibold", step.done ? "text-platforma-success" : "text-platforma-subtle")}>
            {step.done ? <CheckCircle2 aria-hidden="true" size={18} className="shrink-0" /> : <Circle aria-hidden="true" size={18} className="shrink-0" />}
            {t(step.done ? "aiAgents.preparation.complete" : "aiAgents.preparation.required")}
          </span>
          <span className="flex min-w-0 items-center gap-2 text-sm font-semibold text-platforma-ink">
            {Icon && <Icon aria-hidden="true" size={20} className="shrink-0" />}{step.title}
          </span>
          <span className={cn("mt-auto flex min-h-11 items-center justify-between gap-2 rounded-control text-sm font-semibold leading-5", step.done ? "text-platforma-success" : "bg-brand-800 px-3 py-2 text-white")}>
            <span className="min-w-0 break-words">{step.text}</span>
            {!step.done && <ArrowRight aria-hidden="true" size={18} className="shrink-0" />}
          </span>
        </Link>;
      })}
      </nav>
    </section>
  );
}

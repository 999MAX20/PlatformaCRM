import type { ReactNode } from "react";
import { Link } from "react-router";
import { ArrowUpRight, BookOpen, Bot, CheckCircle2, Plus, Radio, Sparkles } from "lucide-react";

import { Card, CardBody } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { useI18n } from "../../../lib/i18n";
import { cn } from "../../../lib/cn";
import type { OnboardingStep } from "../aiAgentsTypes";
export function EmptyAgentsState({ canManage, onCreate }: { canManage: boolean; onCreate: () => void }) {
  const { t } = useI18n();
  return (
    <Card variant="outlined">
      <CardBody className="flex flex-col items-center justify-center py-16 text-center">
        <div className="grid h-14 w-14 place-items-center rounded-2xl bg-ai-600 text-white">
          <Bot size={24} />
        </div>
        <h3 className="mt-4 text-2xl font-black text-midnight">{t("aiAgents.emptyAgentsTitle")}</h3>
        <p className="mt-2 max-w-xl text-sm font-semibold leading-6 text-platforma-faint">
          {t("aiAgents.emptyAgentsText")}
        </p>
        {canManage ? (
          <Button className="mt-5" type="button" onClick={onCreate}>
            <Plus aria-hidden="true" size={16} />
            {t("aiAgents.createAgent")}
          </Button>
        ) : null}
      </CardBody>
    </Card>
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
  const icons = [Bot, BookOpen, Radio];
  return (
    <nav aria-label={t("aiAgents.firstLaunchTitle")} className="grid gap-3 sm:grid-cols-3">
      {steps.map((step, index) => {
        const Icon = icons[index];
        return <Link key={step.href} to={step.href} className={cn(
          "platforma-focus-ring group flex min-w-0 flex-col gap-3 rounded-xl border p-4 transition-colors hover:border-brand-700 hover:bg-brand-50",
          step.done ? "border-platforma-border bg-white" : "border-brand-200 bg-brand-50/50",
        )}>
          <span className="flex items-center justify-between gap-2">
            <Icon aria-hidden="true" size={20} className={step.done ? "text-platforma-subtle" : "text-brand-800"} />
            {step.done ? <CheckCircle2 aria-hidden="true" size={18} className="text-platforma-success" /> : <ArrowUpRight aria-hidden="true" size={18} className="text-brand-800" />}
          </span>
          <span className="min-w-0 break-words">
            <span className="block text-sm font-semibold text-platforma-ink">{step.title}</span>
            <span className={cn("mt-1 block text-sm leading-5", step.done ? "text-platforma-subtle" : "font-medium text-brand-800")}>{step.text}</span>
          </span>
        </Link>;
      })}
    </nav>
  );
}

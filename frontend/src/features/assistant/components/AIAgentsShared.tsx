import type { ReactNode } from "react";
import { Link } from "react-router";
import { Bot, CheckCircle2, Circle, Plus, Sparkles } from "lucide-react";

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

export function OnboardingProgress({
  steps,
  compact = false,
}: {
  steps: Array<{ done: boolean; title: string; text: string; href: string }>;
  compact?: boolean;
}) {
  const { t } = useI18n();
  const doneCount = steps.filter((step) => step.done).length;
  const progress = steps.length ? Math.round((doneCount / steps.length) * 100) : 0;
  if (compact) {
    return (
      <nav aria-label={t("aiAgents.firstLaunchTitle")} className="flex shrink-0 flex-wrap items-center gap-x-4 gap-y-1 border-b border-platforma-border pb-2">
        <span className="text-sm font-semibold text-platforma-subtle">{doneCount}/{steps.length}</span>
        {steps.map(step => {
          const Icon = step.done ? CheckCircle2 : Circle;
          return <Link key={step.title} to={step.href} title={step.text} className="platforma-focus-ring flex min-h-11 items-center gap-2 text-sm text-platforma-text sm:min-h-9">
            <Icon aria-hidden="true" size={16} className={step.done ? "text-platforma-success" : "text-platforma-subtle"} />
            {step.title}
          </Link>;
        })}
      </nav>
    );
  }
  return (
    <div className={cn("rounded-2xl border border-platforma-border bg-white p-4", compact ? "mt-5" : "shadow-sm")}>
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.16em] text-ai-700">{t("aiAgents.firstLaunch")}</p>
          <h3 className="mt-1 font-black text-midnight">{t("aiAgents.firstLaunchTitle")}</h3>
        </div>
        <span className="rounded-full bg-ai-50 px-3 py-1 text-sm font-black text-ai-700 ring-1 ring-ai-100">{doneCount}/{steps.length}</span>
      </div>
      <div className="mt-4 h-2 overflow-hidden rounded-full bg-surface-muted">
        <div className="h-full rounded-full bg-ai-600 transition-all" style={{ width: `${progress}%` }} />
      </div>
      <div className="mt-4 space-y-2">
        {steps.map((step) => (
          <Link
            key={step.title}
            to={step.href}
            className="flex gap-3 rounded-xl p-2 transition hover:bg-surface-hover"
          >
            <span className={cn("mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full text-white", step.done ? "bg-platforma-success" : "bg-platforma-control")}>
              <CheckCircle2 size={14} />
            </span>
            <span className="min-w-0">
              <span className="block text-sm font-black text-midnight">{step.title}</span>
              {!compact ? <span className="mt-1 block text-xs font-semibold leading-5 text-platforma-faint">{step.text}</span> : null}
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}

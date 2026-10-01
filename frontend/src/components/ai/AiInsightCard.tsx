import { ArrowRight, type LucideIcon } from "lucide-react";
import { Link } from "react-router";

import { cn } from "../../lib/cn";

export type AiInsightSeverity = "critical" | "warning" | "good" | "info";

const iconTone: Record<AiInsightSeverity, string> = {
  critical: "border-platforma-danger/20 bg-[var(--platforma-danger-soft)] text-platforma-danger",
  warning: "border-platforma-warning/[0.22] bg-[var(--platforma-warning-soft)] text-platforma-warning",
  good: "border-platforma-success/[0.18] bg-[var(--platforma-success-soft)] text-platforma-success",
  info: "border-ai-100 bg-ai-50 text-ai-700",
};

const severityDot: Record<AiInsightSeverity, string> = {
  critical: "bg-platforma-danger",
  warning: "bg-platforma-warning",
  good: "bg-platforma-success",
  info: "bg-ai-500",
};

export function aiInsightDotClass(severity: AiInsightSeverity) {
  return severityDot[severity];
}

type AiInsightCardProps = {
  title: string;
  description: string;
  actionLabel?: string;
  href?: string;
  icon: LucideIcon;
  severity?: AiInsightSeverity;
  compact?: boolean;
  className?: string;
};

export function AiInsightCard({
  title,
  description,
  actionLabel,
  href,
  icon: Icon,
  severity = "info",
  compact = false,
  className,
}: AiInsightCardProps) {
  const content = (
    <>
      <div
        className={cn(
          "grid shrink-0 place-items-center rounded-card border",
          compact ? "h-10 w-10" : "h-12 w-12",
          iconTone[severity],
        )}
      >
        <Icon size={compact ? 19 : 22} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="font-semibold text-platforma-ink">{title}</p>
        <p className="mt-1 text-sm leading-6 text-platforma-subtle">{description}</p>
      </div>
      {actionLabel ? (
        <div className="inline-flex items-center gap-2 text-sm font-semibold text-ai-700">
          {actionLabel}
          {href ? <ArrowRight size={16} className="transition group-hover:translate-x-1" /> : null}
        </div>
      ) : null}
    </>
  );

  const baseClassName = cn(
    "platforma-ai-surface group flex flex-col gap-4 rounded-card p-4 transition-colors sm:flex-row sm:items-center",
    href ? "hover:border-ai-100" : "",
    className,
  );

  if (!href) {
    return <div className={baseClassName}>{content}</div>;
  }

  return (
    <Link to={href} className={baseClassName}>
      {content}
    </Link>
  );
}

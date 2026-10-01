import type { LucideIcon } from "lucide-react";
import { Link } from "react-router";

import { cn } from "../../lib/cn";

type MetricCardTone = "brand" | "slate" | "emerald" | "amber" | "red";

type MetricCardProps = {
  label: string;
  value: string | number;
  hint?: string;
  icon?: LucideIcon;
  tone?: MetricCardTone;
  href?: string;
  compact?: boolean;
  className?: string;
};

const toneClasses: Record<MetricCardTone, string> = {
  brand: "bg-brand-50 text-brand-700",
  slate: "bg-surface-muted text-platforma-subtle",
  emerald: "bg-[var(--platforma-success-soft)] text-platforma-success",
  amber: "bg-[var(--platforma-warning-soft)] text-platforma-warning",
  red: "bg-[var(--platforma-danger-soft)] text-platforma-danger",
};

export function MetricCard({ label, value, hint, icon: Icon, tone = "brand", href, compact = false, className }: MetricCardProps) {
  const content = (
    <>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-xs font-bold text-platforma-subtle">{label}</p>
          <p className={cn("mt-1.5 font-semibold text-platforma-ink", compact ? "text-xl" : "text-2xl")}>{value}</p>
        </div>
        {Icon ? (
          <div className={cn("grid shrink-0 place-items-center rounded-control", compact ? "h-9 w-9" : "h-10 w-10", toneClasses[tone])}>
            <Icon size={compact ? 18 : 20} />
          </div>
        ) : null}
      </div>
      {hint ? <p className="mt-2 text-sm font-semibold leading-5 text-platforma-subtle">{hint}</p> : null}
    </>
  );
  const classNames = cn(
    "rounded-card border border-platforma-border bg-surface-card shadow-card transition-colors duration-150",
    compact ? "p-3" : "p-4",
    href && "hover:border-brand-100 hover:bg-surface-hover",
    className,
  );

  if (href) {
    return (
      <Link to={href} className={classNames}>
        {content}
      </Link>
    );
  }

  return <div className={classNames}>{content}</div>;
}

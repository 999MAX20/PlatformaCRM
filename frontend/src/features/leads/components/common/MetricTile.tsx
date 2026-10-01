import type { LucideIcon } from "lucide-react";
import type React from "react";

import { cn } from "../../../../lib/cn";

export function MetricTile({
  icon: Icon,
  label,
  value,
  delta,
  tone = "brand",
}: {
  icon: LucideIcon;
  label: string;
  value: React.ReactNode;
  delta?: string;
  tone?: "brand" | "green" | "amber" | "blue" | "pink";
}) {
  const toneClass = {
    brand: "bg-brand-50 text-brand-700",
    green: "bg-[var(--platforma-success-soft)] text-platforma-success",
    amber: "bg-[var(--platforma-warning-soft)] text-platforma-warning",
    blue: "bg-[var(--platforma-info-soft)] text-platforma-info",
    pink: "bg-[var(--platforma-danger-soft)] text-platforma-danger",
  }[tone];
  return (
    <div className="rounded-xl border border-platforma-border bg-white p-4 shadow-soft transition duration-150 hover:-translate-y-0.5 hover:shadow-md">
      <div className="flex items-center gap-2.5">
        <span className={cn("grid h-9 w-9 shrink-0 place-items-center rounded-xl", toneClass)}>
          <Icon size={18} />
        </span>
        <div className="min-w-0">
          <p className="truncate text-xs font-semibold uppercase tracking-[0.04em] text-platforma-faint">{label}</p>
          <div className="mt-1 flex items-end gap-1.5">
            <p className="text-xl font-bold leading-none text-midnight">{value}</p>
            {delta ? <span className="text-xs font-bold text-platforma-success">{delta}</span> : null}
          </div>
        </div>
      </div>
    </div>
  );
}

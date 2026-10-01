import type { ReactNode } from "react";

import { cn } from "../../lib/cn";
import { surfaceClass } from "../ui/Card";

export function CrmTableSurface({
  filters,
  children,
  className,
  filtersClassName,
  frameless = false,
}: {
  filters?: ReactNode;
  children: ReactNode;
  className?: string;
  filtersClassName?: string;
  frameless?: boolean;
}) {
  return (
    <section className={cn(frameless ? "bg-surface-card" : surfaceClass, "flex min-h-0 flex-1 flex-col overflow-hidden", className)}>
      {filters ? <div className={cn("shrink-0 border-b border-platforma-border bg-surface-card", frameless ? "px-3 py-2" : "px-4 py-3", filtersClassName)}>{filters}</div> : null}
      {children}
    </section>
  );
}

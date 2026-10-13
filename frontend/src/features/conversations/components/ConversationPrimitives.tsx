import type { ReactNode } from "react";

import { cn } from "../../../lib/cn";

export function Pill({ children, className }: { children: ReactNode; className?: string }) {
  return <span className={cn("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-bold ring-1", className)}>{children}</span>;
}

export function Tooltip({ label, children, side = "bottom" }: { label: string; children: ReactNode; side?: "top" | "bottom" }) {
  return (
    <span className="group/tooltip relative inline-flex">
      {children}
      <span aria-hidden="true" className={cn("pointer-events-none absolute left-0 z-30 w-max max-w-64 rounded-xl bg-midnight px-3 py-2 text-xs font-bold leading-5 text-white opacity-0 shadow-xl transition group-hover/tooltip:opacity-100 group-focus-within/tooltip:opacity-100", side === "top" ? "bottom-[calc(100%+8px)]" : "top-[calc(100%+8px)]")}>
        {label}
      </span>
    </span>
  );
}

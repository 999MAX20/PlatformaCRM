import { cn } from "../../../../lib/cn";
import type { PipelineStage } from "../../../../types";
import type { Translate } from "../../types";

export function DealStageBadge({
  stage,
  fallback,
}: {
  stage?: PipelineStage;
  fallback: string;
}) {
  return (
    <span className="inline-flex max-w-full items-center gap-2 rounded-lg bg-brand-50 px-2.5 py-1 text-xs font-bold text-brand-700">
      <span
        className="h-2 w-2 shrink-0 rounded-full"
        style={{ backgroundColor: stage?.color || "#F5B37A" }}
      />
      <span className="truncate">{stage?.name || fallback}</span>
    </span>
  );
}

export function StatusPill({
  status,
  t,
}: {
  status: "open" | "won" | "lost";
  t: Translate;
}) {
  const label =
    status === "won"
      ? t("deals.statusWon")
      : status === "lost"
        ? t("deals.statusLost")
        : t("deals.statusOpen");
  return (
    <span
      className={cn(
        "inline-flex rounded-lg px-2.5 py-1 text-xs font-bold",
        status === "won" && "bg-[var(--platforma-success-soft)] text-platforma-success",
        status === "lost" && "bg-[var(--platforma-danger-soft)] text-platforma-danger",
        status === "open" && "bg-surface-muted text-platforma-muted",
      )}
    >
      {label}
    </span>
  );
}

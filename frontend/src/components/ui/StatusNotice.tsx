import { AlertCircle, AlertTriangle, CheckCircle2, Info, type LucideIcon } from "lucide-react";
import type { HTMLAttributes, ReactNode } from "react";

import type { AppError } from "../../api/appError";
import { cn } from "../../lib/cn";

export type StatusNoticeTone = "success" | "info" | "warning" | "danger";

type ToneDefinition = {
  Icon: LucideIcon;
  container: string;
  icon: string;
};

export const statusNoticeTones: Record<StatusNoticeTone, ToneDefinition> = {
  success: {
    Icon: CheckCircle2,
    container: "border-platforma-success/[0.18] bg-[var(--platforma-success-soft)]",
    icon: "text-platforma-success",
  },
  info: {
    Icon: Info,
    container: "border-platforma-info/[0.18] bg-[var(--platforma-info-soft)]",
    icon: "text-platforma-info",
  },
  warning: {
    Icon: AlertTriangle,
    container: "border-platforma-warning/[0.22] bg-[var(--platforma-warning-soft)]",
    icon: "text-platforma-warning",
  },
  danger: {
    Icon: AlertCircle,
    container: "border-platforma-danger/20 bg-[var(--platforma-danger-soft)]",
    icon: "text-platforma-danger",
  },
};

export function appErrorNoticeTone(error: AppError): StatusNoticeTone {
  if (error.category === "not_found") return "info";
  if (["authentication", "permission", "conflict", "rate_limit", "offline", "provider"].includes(error.category)) {
    return "warning";
  }
  return "danger";
}

type StatusNoticeProps = Omit<HTMLAttributes<HTMLDivElement>, "title"> & {
  action?: ReactNode;
  actionPlacement?: "center" | "corner";
  ariaLive?: "assertive" | "off" | "polite";
  compact?: boolean;
  description?: ReactNode;
  details?: ReactNode;
  icon?: LucideIcon;
  iconClassName?: string;
  title: ReactNode;
  tone?: StatusNoticeTone;
};

export function StatusNotice({
  action,
  actionPlacement = "center",
  ariaLive,
  className,
  compact = false,
  description,
  details,
  icon: IconOverride,
  iconClassName,
  role,
  title,
  tone = "info",
  ...props
}: StatusNoticeProps) {
  const definition = statusNoticeTones[tone];
  const Icon = IconOverride || definition.Icon;
  const resolvedRole = role || (tone === "danger" ? "alert" : "status");
  const resolvedLive = ariaLive || (resolvedRole === "alert" ? "assertive" : "polite");

  return (
    <div
      {...props}
      role={resolvedRole}
      aria-live={resolvedLive}
      className={cn(
        "rounded-card border text-platforma-text shadow-sm",
        compact ? "p-3" : "p-4",
        definition.container,
        className,
      )}
    >
      <div className={cn("flex gap-3", actionPlacement === "corner" ? "flex-row items-start justify-between" : "flex-col sm:flex-row sm:items-center sm:justify-between")}>
        <div className="flex min-w-0 items-start gap-3">
          <Icon
            aria-hidden="true"
            className={cn("mt-0.5 shrink-0", definition.icon, iconClassName)}
            size={18}
          />
          <div className="min-w-0">
            <p className="text-sm font-semibold text-platforma-ink">{title}</p>
            {description ? <div className="mt-1 text-sm leading-6 text-platforma-subtle">{description}</div> : null}
          </div>
        </div>
        {action ? <div className={cn("flex shrink-0 flex-wrap items-center justify-center gap-2", actionPlacement === "center" && "sm:justify-end")}>{action}</div> : null}
      </div>
      {details ? <div className="mt-3">{details}</div> : null}
    </div>
  );
}

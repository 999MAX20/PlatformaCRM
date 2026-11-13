import { AlertCircle, AlertTriangle, CheckCircle2, Info, type LucideIcon } from "lucide-react";
import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "../../lib/cn";
import type { StatusNoticeTone } from "./statusNoticePolicy";

export { appErrorNoticeTone, type StatusNoticeTone } from "./statusNoticePolicy";

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

type StatusNoticeProps = Omit<HTMLAttributes<HTMLDivElement>, "title"> & {
  action?: ReactNode;
  dismiss?: ReactNode;
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
  dismiss,
  actionPlacement: _actionPlacement,
  ariaLive,
  className,
  compact: _compact,
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
      aria-atomic="true"
      data-notice-tone={tone}
      className={cn(
        "platforma-status-notice",
        className,
      )}
    >
      <div className="platforma-notice-grid">
          <Icon
            aria-hidden="true"
            className={cn("platforma-notice-icon", iconClassName)}
            size={20}
          />
          <div className="min-w-0">
            <p className="platforma-notice-title">{title}</p>
            {description ? <div className="platforma-notice-description">{description}</div> : null}
          </div>
          {dismiss ? <div className="platforma-notice-dismiss">{dismiss}</div> : null}
      </div>
      {details ? <div className="mt-3">{details}</div> : null}
      {action ? <div className="platforma-notice-actions">{action}</div> : null}
    </div>
  );
}

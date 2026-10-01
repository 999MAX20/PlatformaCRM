import { cn } from "../../lib/cn";

export type BadgeVariant = "neutral" | "primary" | "success" | "warning" | "danger" | "info" | "discovery" | "ai";
export type BadgeSize = "sm" | "md" | "lg";

export const badgeVariants: Record<BadgeVariant, string> = {
  neutral: "bg-surface-muted text-platforma-subtle ring-platforma-border",
  primary: "bg-brand-50 text-brand-700 ring-brand-100",
  success: "bg-[var(--platforma-success-soft)] text-platforma-success ring-platforma-success/[0.18]",
  warning: "bg-[var(--platforma-warning-soft)] text-platforma-warning ring-platforma-warning/[0.24]",
  danger: "bg-[var(--platforma-danger-soft)] text-platforma-danger ring-platforma-danger/20",
  info: "bg-[var(--platforma-info-soft)] text-platforma-info ring-platforma-info/20",
  discovery: "bg-discovery-50 text-discovery-700 ring-discovery-100",
  ai: "bg-ai-50 text-ai-700 ring-ai-100",
};

const sizes: Record<BadgeSize, string> = {
  sm: "min-h-5 px-2 py-0.5 text-[11px]",
  md: "min-h-6 px-2.5 py-1 text-xs",
  lg: "min-h-7 px-3 py-1 text-[13px]",
};

export function Badge({
  children,
  variant = "neutral",
  size = "md",
  className,
}: {
  children: React.ReactNode;
  variant?: BadgeVariant;
  size?: BadgeSize;
  className?: string;
}) {
  return (
    <span className={cn("inline-flex max-w-full items-center gap-1 rounded-full font-semibold leading-none ring-1", badgeVariants[variant], sizes[size], className)}>
      {children}
    </span>
  );
}

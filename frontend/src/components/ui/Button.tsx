import { ButtonHTMLAttributes, forwardRef } from "react";
import { twMerge } from "tailwind-merge";

import { cn } from "../../lib/cn";
import { useI18n } from "../../lib/i18n";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "outline" | "warning" | "danger" | "ai" | "icon";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: "sm" | "md" | "lg" | "icon";
  isLoading?: boolean;
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant = "primary", size = "md", isLoading, children, disabled, ...props },
  ref,
) {
  const { t } = useI18n();
  const variants = {
    primary: "bg-brand-500 text-white shadow-xs ring-1 ring-brand-600/20 hover:bg-brand-600 active:bg-[var(--platforma-brand-strong)]",
    secondary: "border border-platforma-control bg-surface-card text-platforma-text shadow-xs hover:bg-surface-hover active:bg-surface-muted",
    ghost: "text-platforma-subtle hover:bg-surface-hover hover:text-platforma-text active:bg-surface-muted",
    outline: "border border-platforma-control bg-surface-card text-platforma-text shadow-xs hover:bg-surface-hover active:bg-surface-muted",
    warning: "bg-[var(--platforma-warning-bold)] text-platforma-warning shadow-xs ring-1 ring-platforma-warning/40 hover:bg-[var(--platforma-warning-bold-hover)] active:bg-[var(--platforma-warning-bold-pressed)]",
    danger: "bg-platforma-danger text-white shadow-xs hover:bg-[var(--platforma-danger-hover)] active:bg-[var(--platforma-danger-pressed)]",
    ai: "bg-ai-600 text-white shadow-xs hover:bg-ai-700 active:bg-ai-700",
    icon: "border border-platforma-control bg-surface-card text-platforma-subtle shadow-xs hover:bg-surface-hover hover:text-platforma-text active:bg-surface-muted",
  };
  const sizes = {
    sm: "min-h-9 rounded-control px-3 py-1.5 text-[13px]",
    md: "min-h-10 rounded-control px-4 py-2 text-sm",
    lg: "min-h-11 rounded-control px-5 py-2.5 text-[15px]",
    icon: "h-10 w-10 rounded-control p-0",
  };

  return (
    <button
      ref={ref}
      className={twMerge(cn(
        "inline-flex max-w-full items-center justify-center gap-2 whitespace-normal text-center font-semibold transition duration-150 active:scale-[0.99] disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-100",
        "focus-visible:outline-hidden focus-visible:ring-4 focus-visible:ring-[var(--platforma-focus-ring)] focus-visible:ring-offset-2",
        "disabled:border-disabled-border disabled:bg-disabled-surface disabled:text-disabled-content disabled:shadow-none disabled:ring-1 disabled:ring-disabled-border",
        variants[variant],
        sizes[size],
        className,
      ))}
      disabled={disabled || isLoading}
      aria-busy={isLoading || undefined}
      {...props}
    >
      {isLoading ? t("common.loading") : children}
    </button>
  );
});

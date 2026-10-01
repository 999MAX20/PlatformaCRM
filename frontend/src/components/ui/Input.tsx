import { InputHTMLAttributes, ReactNode, forwardRef, useId } from "react";

import { cn } from "../../lib/cn";

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  error?: string;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
};

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, leftIcon, rightIcon, className, "aria-describedby": describedBy, ...props }, ref) => {
    const errorId = useId();
    const resolvedDescribedBy = [describedBy, error ? errorId : null].filter(Boolean).join(" ") || undefined;

    return (
      <label className="block">
        {label ? <span className="mb-2 block text-sm font-semibold text-platforma-subtle">{label}</span> : null}
        <span className="relative block">
          {leftIcon ? <span aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-platforma-faint">{leftIcon}</span> : null}
          <input
            ref={ref}
            aria-describedby={resolvedDescribedBy}
            aria-invalid={error ? "true" : undefined}
            className={cn(
              "platforma-focus-ring min-h-11 w-full rounded-control border border-platforma-control bg-surface-card px-3 text-sm font-medium text-platforma-text shadow-sm placeholder:text-platforma-faint",
              "hover:border-brand-500 disabled:cursor-not-allowed disabled:border-disabled-border disabled:bg-disabled-surface disabled:text-disabled-content disabled:opacity-100 read-only:bg-surface-warm read-only:text-platforma-subtle",
              leftIcon && "pl-10",
              rightIcon && "pr-10",
              error && "border-platforma-danger hover:border-platforma-danger focus-visible:border-platforma-danger focus-visible:ring-platforma-danger/[0.18]",
              className,
            )}
            {...props}
          />
          {rightIcon ? <span className="absolute right-3 top-1/2 -translate-y-1/2 text-platforma-faint">{rightIcon}</span> : null}
        </span>
        {error ? <span id={errorId} role="alert" className="mt-1.5 block text-xs font-semibold text-platforma-danger">{error}</span> : null}
      </label>
    );
  },
);

Input.displayName = "Input";

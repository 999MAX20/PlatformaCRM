import { TextareaHTMLAttributes, forwardRef, useId } from "react";

import { cn } from "../../lib/cn";

type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label?: string;
  error?: string;
};

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, className, "aria-describedby": describedBy, ...props }, ref) => {
    const errorId = useId();
    const resolvedDescribedBy = [describedBy, error ? errorId : null].filter(Boolean).join(" ") || undefined;

    return (
      <label className="block">
        {label ? <span className="mb-2 block text-sm font-semibold text-platforma-subtle">{label}</span> : null}
        <textarea
          ref={ref}
          aria-describedby={resolvedDescribedBy}
          aria-invalid={error ? "true" : undefined}
          className={cn(
            "platforma-focus-ring min-h-24 w-full resize-y rounded-control border border-platforma-control bg-surface-card px-3 py-2.5 text-sm font-medium leading-6 text-platforma-text shadow-sm placeholder:text-platforma-faint",
            "hover:border-brand-500 disabled:cursor-not-allowed disabled:border-disabled-border disabled:bg-disabled-surface disabled:text-disabled-content disabled:opacity-100 read-only:bg-surface-warm read-only:text-platforma-subtle",
            error && "border-platforma-danger hover:border-platforma-danger focus-visible:border-platforma-danger focus-visible:ring-platforma-danger/[0.18]",
            className,
          )}
          {...props}
        />
        {error ? <span id={errorId} role="alert" className="mt-1.5 block text-xs font-semibold text-platforma-danger">{error}</span> : null}
      </label>
    );
  },
);

Textarea.displayName = "Textarea";

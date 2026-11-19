import { InputHTMLAttributes, ReactNode, forwardRef, useId, useState } from "react";
import { Eye, EyeOff } from "lucide-react";

import { cn } from "../../lib/cn";
import { useI18n } from "../../lib/i18n";
import { CalendarInput } from "./CalendarInput";

export type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  error?: string;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  pageSearch?: boolean;
  passwordReveal?: boolean;
};

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, leftIcon, rightIcon, pageSearch = false, passwordReveal = true, className, "aria-describedby": describedBy, ...props }, ref) => {
    const errorId = useId();
    const { t } = useI18n();
    const [passwordVisible, setPasswordVisible] = useState(false);
    const hasPasswordToggle = props.type === "password" && passwordReveal && !rightIcon;
    const resolvedDescribedBy = [describedBy, error ? errorId : null].filter(Boolean).join(" ") || undefined;

    if (props.type === "date" || props.type === "datetime-local") {
      return <CalendarInput ref={ref} label={label} error={error} leftIcon={leftIcon} rightIcon={rightIcon} className={className} aria-describedby={describedBy} {...props} />;
    }

    return (
      <label className={cn("block", pageSearch && "max-w-full min-w-0 shrink-0")} style={pageSearch ? { width: "var(--global-search-width,480px)" } : undefined}>
        {label ? <span className="mb-2 block text-sm font-semibold text-platforma-subtle">{label}</span> : null}
        <span className="relative block">
          {leftIcon ? <span aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-platforma-faint">{leftIcon}</span> : null}
          <input
            ref={ref}
            aria-describedby={resolvedDescribedBy}
            aria-invalid={error ? "true" : undefined}
            aria-label={hasPasswordToggle ? label : undefined}
            className={cn(
              "platforma-focus-ring min-h-11 w-full rounded-control border border-platforma-control bg-surface-card px-3 text-sm font-medium text-platforma-text shadow-xs placeholder:text-platforma-faint",
              "hover:border-brand-500 disabled:cursor-not-allowed disabled:border-disabled-border disabled:bg-disabled-surface disabled:text-disabled-content disabled:opacity-100 read-only:bg-surface-warm read-only:text-platforma-subtle",
              leftIcon && "pl-10",
              rightIcon && "pr-10",
              hasPasswordToggle && "pr-12",
              error && "border-platforma-danger hover:border-platforma-danger focus-visible:border-platforma-danger focus-visible:ring-platforma-danger/[0.18]",
              className,
            )}
            {...props}
            type={hasPasswordToggle && passwordVisible ? "text" : props.type}
          />
          {hasPasswordToggle ? (
            <button
              type="button"
              className="platforma-focus-ring absolute right-0 top-1/2 flex h-11 w-11 -translate-y-1/2 cursor-pointer items-center justify-center rounded-control text-platforma-subtle disabled:cursor-not-allowed disabled:opacity-50"
              aria-label={t(passwordVisible ? "auth.hidePassword" : "auth.showPassword")}
              aria-pressed={passwordVisible}
              disabled={props.disabled}
              onClick={() => setPasswordVisible(value => !value)}
            >
              {passwordVisible ? <EyeOff size={18} aria-hidden="true" /> : <Eye size={18} aria-hidden="true" />}
            </button>
          ) : null}
          {rightIcon ? <span className="absolute right-3 top-1/2 -translate-y-1/2 text-platforma-faint">{rightIcon}</span> : null}
        </span>
        {error ? <span id={errorId} role="alert" className="mt-1.5 block text-xs font-semibold text-platforma-danger">{error}</span> : null}
      </label>
    );
  },
);

Input.displayName = "Input";

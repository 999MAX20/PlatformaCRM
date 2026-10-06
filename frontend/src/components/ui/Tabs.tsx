import type { KeyboardEvent } from "react";

import { cn } from "../../lib/cn";

export function Tabs<T extends string>({
  value,
  options,
  onChange,
  ariaLabel,
  className,
  idPrefix,
  tone = "brand",
  appearance = "pill",
}: {
  value: T;
  options: Array<{ value: T; label: string; count?: number }>;
  onChange: (value: T) => void;
  ariaLabel: string;
  className?: string;
  idPrefix?: string;
  tone?: "brand" | "ai";
  appearance?: "pill" | "underline";
}) {
  const selectFromKeyboard = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    let nextIndex: number | null = null;
    if (event.key === "ArrowRight") nextIndex = (index + 1) % options.length;
    if (event.key === "ArrowLeft") nextIndex = (index - 1 + options.length) % options.length;
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = options.length - 1;
    if (nextIndex === null) return;

    event.preventDefault();
    const tabs = event.currentTarget.parentElement?.querySelectorAll<HTMLButtonElement>('[role="tab"]');
    tabs?.[nextIndex]?.focus();
    onChange(options[nextIndex].value);
  };

  return (
    <div className={cn("flex gap-1 overflow-x-auto no-scrollbar", appearance === "underline" ? "border-b border-platforma-border" : "rounded-control bg-surface-muted p-1", className)} role="tablist" aria-label={ariaLabel}>
      {options.map((option, index) => {
        const active = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            className={cn(
              "platforma-focus-ring inline-flex min-h-9 shrink-0 items-center justify-center gap-2 px-3 text-sm font-semibold transition",
              appearance === "underline" ? "border-b-2 py-2" : "flex-1 rounded-control",
              appearance === "underline"
                ? active
                  ? tone === "ai" ? "border-ai-600 text-ai-700" : "border-brand-500 text-brand-700"
                  : "border-transparent text-platforma-subtle hover:bg-surface-hover hover:text-platforma-text"
                : active
                ? tone === "ai"
                  ? "bg-ai-50 text-ai-700 shadow-xs ring-1 ring-ai-100"
                  : "bg-brand-50 text-brand-700 shadow-xs ring-1 ring-brand-100"
                : "text-platforma-subtle hover:bg-surface-hover hover:text-platforma-text",
            )}
            role="tab"
            id={idPrefix ? `${idPrefix}-tab-${option.value}` : undefined}
            aria-controls={idPrefix ? `${idPrefix}-panel-${option.value}` : undefined}
            aria-selected={active}
            tabIndex={active ? 0 : -1}
            onClick={() => onChange(option.value)}
            onKeyDown={(event) => selectFromKeyboard(event, index)}
          >
            <span className="min-w-0 truncate">{option.label}</span>
            {typeof option.count === "number" ? (
              <span className={cn("shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold", active ? "bg-surface-muted text-platforma-subtle" : "bg-surface-card text-platforma-faint")}>
                {option.count}
              </span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}

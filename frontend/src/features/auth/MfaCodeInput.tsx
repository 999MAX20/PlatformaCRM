import { useId, useRef, useState } from "react";

import { cn } from "../../lib/cn";

type Props = {
  label: string;
  value: string;
  disabled: boolean;
  onChange: (value: string) => void;
};

export function MfaCodeInput({ label, value, disabled, onChange }: Props) {
  const id = useId();
  const input = useRef<HTMLInputElement>(null);
  const [focused, setFocused] = useState(false);
  const [position, setPosition] = useState(0);

  function selectPosition(index: number) {
    const next = Math.min(index, value.length);
    input.current?.setSelectionRange(next, Math.min(next + 1, value.length));
    setPosition(next);
  }

  return <div className="mx-auto w-full max-w-80" data-testid="mfa-code-input">
    <label htmlFor={id} className="mb-2 block text-center text-sm font-semibold text-platforma-subtle">{label}</label>
    <div className="relative">
      <input
        ref={input}
        id={id}
        value={value}
        type="text"
        inputMode="numeric"
        autoComplete="one-time-code"
        pattern="[0-9]{6}"
        maxLength={6}
        required
        disabled={disabled}
        className="absolute inset-0 z-10 h-full w-full cursor-text opacity-0 disabled:cursor-not-allowed"
        onFocus={event => { setFocused(true); setPosition(event.currentTarget.selectionStart || 0); }}
        onBlur={() => setFocused(false)}
        onSelect={event => setPosition(event.currentTarget.selectionStart || 0)}
        onClick={event => {
          const rect = event.currentTarget.getBoundingClientRect();
          selectPosition(Math.min(5, Math.floor((event.clientX - rect.left) / rect.width * 6)));
        }}
        onChange={event => onChange(event.currentTarget.value.replace(/\D/g, "").slice(0, 6))}
        onPaste={event => {
          event.preventDefault();
          const pasted = event.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
          if (pasted) {
            onChange(pasted);
            requestAnimationFrame(() => {
              input.current?.setSelectionRange(pasted.length, pasted.length);
              setPosition(pasted.length);
            });
          }
        }}
      />
      <div aria-hidden="true" className="grid grid-cols-6 gap-1.5 sm:gap-2">
        {Array.from({ length: 6 }, (_, index) => <span key={index} className={cn(
          "grid h-14 min-w-0 place-items-center rounded-control border border-platforma-control bg-surface-card text-xl font-semibold tabular-nums text-platforma-text",
          focused && Math.min(position, 5) === index && "border-brand-600 ring-2 ring-brand-600 ring-offset-2",
          disabled && "border-disabled-border bg-disabled-surface text-disabled-content",
        )}>{value[index] || ""}</span>)}
      </div>
    </div>
  </div>;
}

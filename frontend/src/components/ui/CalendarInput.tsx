import { CalendarDays } from "lucide-react";
import { forwardRef, useId, useRef, useState } from "react";
import { cn } from "../../lib/cn";
import { useI18n } from "../../lib/i18n";
import { Button } from "./Button";
import { CalendarPopover } from "./CalendarPopover";
import { DateRangePicker, isCalendarDate } from "./DateRangePicker";
import type { InputProps } from "./Input";

const inputClass = "platforma-focus-ring min-h-11 w-full min-w-0 rounded-control border border-platforma-control bg-surface-card px-3 text-sm font-medium text-platforma-text shadow-xs placeholder:text-platforma-faint hover:border-brand-500 disabled:cursor-not-allowed disabled:border-disabled-border disabled:bg-disabled-surface disabled:text-disabled-content disabled:opacity-100 read-only:bg-surface-warm read-only:text-platforma-subtle";

export const CalendarInput = forwardRef<HTMLInputElement, InputProps>(function CalendarInput(
  { label, error, leftIcon, rightIcon, className, id: suppliedId, "aria-describedby": describedBy, ...props }, ref,
) {
  const { t } = useI18n();
  const generatedId = useId();
  const id = suppliedId || generatedId;
  const input = useRef<HTMLInputElement>(null);
  const anchor = useRef<HTMLButtonElement>(null);
  const [draft, setDraft] = useState<string | null>(null);
  const dateTime = props.type === "datetime-local";
  const disabled = props.disabled || props.readOnly;
  const today = new Date();
  const todayKey = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
  const current = draft || "";
  const date = current.split("T")[0];
  const time = current.split("T")[1] || "";
  const calendarLabel = label || props["aria-label"] || t("appointment.date");
  const min = typeof props.min === "string" ? props.min : undefined;
  const max = typeof props.max === "string" ? props.max : undefined;
  const check = document.createElement("input");
  check.type = props.type || "date";
  check.required = Boolean(props.required);
  if (min) check.min = min;
  if (max) check.max = max;
  if (props.step !== undefined) check.step = String(props.step);
  check.value = current;
  const valid = check.value === current && check.checkValidity() && (!current || isCalendarDate(date));
  function close(restore = true) { setDraft(null); if (restore) anchor.current?.focus(); }
  function commit(value: string) {
    if (!input.current || disabled) return;
    // Use a native input event so controlled forms and register() receive the same value.
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set?.call(input.current, value);
    input.current.dispatchEvent(new Event("input", { bubbles: true }));
    close();
  }
  function open() { if (!disabled) setDraft(input.current?.value || ""); }
  return <div className="platforma-calendar-field block min-w-0" data-disabled={disabled || undefined}>
    {label && <label htmlFor={id} className="mb-2 block text-sm font-semibold text-platforma-subtle">{label}</label>}
    <div className="relative">
      {leftIcon && <span aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-platforma-faint">{leftIcon}</span>}
      <input {...props} id={id} ref={node => { input.current = node; if (typeof ref === "function") ref(node); else if (ref) ref.current = node; }}
        aria-describedby={[describedBy, error ? `${id}-error` : null].filter(Boolean).join(" ") || undefined} aria-invalid={error ? "true" : props["aria-invalid"]}
        className={cn(inputClass, "pr-12 [&::-webkit-calendar-picker-indicator]:hidden", leftIcon && "pl-10", error && "border-platforma-danger hover:border-platforma-danger focus-visible:border-platforma-danger focus-visible:ring-platforma-danger/[0.18]", className)}
        onClick={event => { props.onClick?.(event); event.preventDefault(); event.currentTarget.focus(); }}
        onKeyDown={event => {
          props.onKeyDown?.(event);
          if (!event.defaultPrevented && (event.key === "F4" || event.key === " " || (event.altKey && event.key === "ArrowDown"))) { event.preventDefault(); open(); }
        }} />
      <Button ref={anchor} type="button" variant="ghost" size="icon" className="absolute right-0 top-0 h-11 w-11" disabled={disabled}
        aria-label={t("calendar.openPicker", { label: calendarLabel })} aria-haspopup="dialog" aria-expanded={draft !== null} aria-controls={draft !== null ? `${id}-calendar` : undefined}
        onClick={() => draft === null ? open() : close()}><CalendarDays size={18} /></Button>
      {rightIcon && <span className="text-platforma-faint">{rightIcon}</span>}
    </div>
    {error && <span id={`${id}-error`} role="alert" className="mt-1.5 block text-xs font-semibold text-platforma-danger">{error}</span>}
    {draft !== null && !disabled && <CalendarPopover anchor={anchor} label={calendarLabel} id={`${id}-calendar`} onClose={close}>
      <DateRangePicker inline range={false} allowClear={false} label={calendarLabel} value={{ from: date, to: date }} today={todayKey} min={min?.slice(0, 10)} max={max?.slice(0, 10)}
        onChange={next => dateTime ? setDraft(`${next.from}T${time}`) : commit(next.from)} />
      {dateTime && <label className="mt-3 block text-sm font-medium">{t("appointment.time")}
        <input type="time" className={cn(inputClass, "mt-1.5")} value={time} step={props.step} required onChange={event => setDraft(`${date}T${event.target.value}`)} />
      </label>}
      <div className="mt-3 flex flex-wrap justify-end gap-2 border-t border-platforma-border pt-3">
        {!props.required && <Button type="button" variant="ghost" className="mr-auto min-h-11" onClick={() => commit("")}>{t("common.clear")}</Button>}
        <Button type="button" variant="secondary" className="min-h-11" onClick={() => close()}>{t("common.cancel")}</Button>
        {dateTime && <Button type="button" className="min-h-11" disabled={!valid || !current} onClick={() => { if (valid) commit(current); }}>{t("crmFilters.apply")}</Button>}
      </div>
    </CalendarPopover>}
  </div>;
});

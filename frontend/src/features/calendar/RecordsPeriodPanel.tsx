import { useEffect, useLayoutEffect, useRef, useState, type RefObject } from "react";
import { createPortal } from "react-dom";
import { Button } from "../../components/ui/Button";
import { PopoverSurface } from "../../components/ui/Overlay";
import { DateRangePicker, isCalendarDate, type DateRangeValue } from "../../components/ui/DateRangePicker";
import { useI18n } from "../../lib/i18n";

export function RecordsPeriodPanel({ from, to, today, anchor, onApply, onClose }: {
  from: string; to: string; today: string;
  anchor: RefObject<HTMLButtonElement | null>;
  onApply: (range: DateRangeValue) => void; onClose: (restoreFocus?: boolean) => void;
}) {
  const { t } = useI18n();
  const panel = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ left: 8, top: 8, maxHeight: 400 });
  const [draft, setDraft] = useState({ from, to });
  const valid = isCalendarDate(draft.from) && isCalendarDate(draft.to) && draft.from <= draft.to;
  useLayoutEffect(() => {
    const place = () => {
      const rect = anchor.current?.getBoundingClientRect();
      if (!rect || !panel.current) return;
      const width = panel.current.offsetWidth;
      const below = window.innerHeight - rect.bottom - 14;
      const above = rect.top - 14;
      const upward = below < panel.current.scrollHeight && above > below;
      const maxHeight = Math.max(80, upward ? above : below);
      setPosition({ left: Math.max(8, Math.min(rect.left, window.innerWidth - width - 8)),
        top: upward ? Math.max(8, rect.top - Math.min(panel.current.scrollHeight, maxHeight) - 6) : rect.bottom + 6, maxHeight });
    };
    place();
    panel.current?.querySelector<HTMLButtonElement>('[data-date][tabindex="0"]')?.focus({ preventScroll: true });
    const observer = new ResizeObserver(place);
    if (panel.current) observer.observe(panel.current);
    window.addEventListener("resize", place);
    window.addEventListener("scroll", place, true);
    return () => { observer.disconnect(); window.removeEventListener("resize", place); window.removeEventListener("scroll", place, true); };
  }, [anchor]);
  useEffect(() => {
    const outside = (event: PointerEvent | FocusEvent) => {
      if (!panel.current?.contains(event.target as Node) && !anchor.current?.contains(event.target as Node)) onClose(false);
    };
    document.addEventListener("pointerdown", outside);
    document.addEventListener("focusin", outside);
    return () => { document.removeEventListener("pointerdown", outside); document.removeEventListener("focusin", outside); };
  }, [anchor, onClose]);
  return createPortal(<PopoverSurface ref={panel} id="records-period-panel" role="dialog" aria-label={t("analyticsWorkspace.period")}
    className="fixed z-[var(--platforma-z-popover)] w-[min(384px,calc(100vw-1rem))] overflow-y-auto p-3 sm:p-4" style={position}
    onKeyDown={event => { if (event.key === "Escape" && !event.defaultPrevented) { event.preventDefault(); event.stopPropagation(); onClose(); } }}>
    <DateRangePicker inline compact allowClear={false} showHint={false} showPresets={false} label={t("analyticsWorkspace.period")} value={draft} onChange={setDraft} today={today} />
    <div className="mt-3 flex justify-end gap-2 border-t border-platforma-border pt-3">
      <Button variant="secondary" onClick={() => onClose()}>{t("common.cancel")}</Button>
      <Button disabled={!valid} onClick={() => { if (valid) onApply(draft); }}>{t("crmFilters.apply")}</Button>
    </div>
  </PopoverSurface>, document.body);
}

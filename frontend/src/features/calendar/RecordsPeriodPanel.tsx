import { useEffect, useRef, useState } from "react";
import { Button } from "../../components/ui/Button";
import { DateRangePicker, isCalendarDate, type DateRangeValue } from "../../components/ui/DateRangePicker";
import { useI18n } from "../../lib/i18n";

export function RecordsPeriodPanel({ from, to, today, onApply, onClose }: {
  from: string; to: string; today: string;
  onApply: (range: DateRangeValue) => void; onClose: () => void;
}) {
  const { t } = useI18n();
  const panel = useRef<HTMLElement>(null);
  const [draft, setDraft] = useState({ from, to });
  const valid = isCalendarDate(draft.from) && isCalendarDate(draft.to) && draft.from <= draft.to;
  useEffect(() => { panel.current?.querySelector<HTMLButtonElement>('[data-date][tabindex="0"]')?.focus(); }, []);
  return <section ref={panel} id="records-period-panel" aria-label={t("analyticsWorkspace.period")}
    className="mt-3 w-full max-w-sm rounded-card border border-platforma-border bg-surface-card p-3 sm:p-4"
    onKeyDown={event => { if (event.key === "Escape" && !event.defaultPrevented) { event.preventDefault(); event.stopPropagation(); onClose(); } }}>
    <DateRangePicker inline compact allowClear={false} label={t("analyticsWorkspace.period")} value={draft} onChange={setDraft} today={today} />
    <div className="mt-3 flex justify-end gap-2 border-t border-platforma-border pt-3">
      <Button variant="secondary" onClick={onClose}>{t("common.cancel")}</Button>
      <Button disabled={!valid} onClick={() => { if (valid) onApply(draft); }}>{t("crmFilters.apply")}</Button>
    </div>
  </section>;
}

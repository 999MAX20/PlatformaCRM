import type { RefObject } from "react";
import { DatePickerPanel, type DateRangeValue } from "../../components/ui/DateRangePicker";
import { useI18n } from "../../lib/i18n";

export function RecordsPeriodPanel({ from, to, today, anchor, onApply, onClose }: {
  from: string; to: string; today: string;
  anchor: RefObject<HTMLButtonElement | null>;
  onApply: (range: DateRangeValue) => void; onClose: (restoreFocus?: boolean) => void;
}) {
  const { t } = useI18n();
  return <DatePickerPanel id="records-period-panel" label={t("analyticsWorkspace.period")}
    value={{ from, to }} today={today} anchor={anchor} onApply={onApply} onClose={onClose} />;
}

import { CalendarDays } from "lucide-react";
import { useState } from "react";
import { Button } from "../../../components/ui/Button";
import { DateRangePicker } from "../../../components/ui/DateRangePicker";
import { Modal } from "../../../components/ui/Modal";
import { useI18n } from "../../../lib/i18n";
import { formatPickerDate } from "../calendarUtils";

export function CalendarPicker({ value, onChange, locale, todayValue, periodLabel }: {
  value: string; onChange: (value: string) => void; locale: string; todayValue: string; periodLabel?: string;
}) {
  const [open, setOpen] = useState(false);
  const { t } = useI18n();
  return <div className="min-w-0 flex-1 sm:flex-none">
    <Button variant="secondary" className="min-h-10 w-full justify-between gap-2 px-3 sm:min-w-[210px]" aria-haspopup="dialog" aria-expanded={open} data-testid="calendar-period-picker" onClick={() => setOpen(true)}>
      <span className="whitespace-normal text-left">{periodLabel || formatPickerDate(value, locale)}</span><CalendarDays size={18} className="shrink-0" />
    </Button>
    <Modal title={t("calendar.selectedDay")} open={open} onClose={() => setOpen(false)} size="sm" testId="calendar-date-picker">
      <DateRangePicker inline range={false} label={t("calendar.selectedDay")} value={{ from: value, to: value }} today={todayValue} onChange={next => { onChange(next.from); setOpen(false); }} />
    </Modal>
  </div>;
}

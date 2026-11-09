import { CalendarDays } from "lucide-react";
import { useRef, useState } from "react";
import { Button } from "../../../components/ui/Button";
import { DatePickerPanel } from "../../../components/ui/DateRangePicker";
import { useI18n } from "../../../lib/i18n";
import { formatPickerDate } from "../calendarUtils";
import { useAppointmentYears } from "../useAppointmentYears";

export function CalendarPicker({ value, onChange, locale, todayValue, periodLabel }: {
  value: string; onChange: (value: string) => void; locale: string; todayValue: string; periodLabel?: string;
}) {
  const [open, setOpen] = useState(false);
  const yearRange = useAppointmentYears(todayValue, open);
  const anchor = useRef<HTMLButtonElement>(null);
  const close = (restore = true) => { setOpen(false); if (restore) anchor.current?.focus(); };
  const { t } = useI18n();
  return <div className="shrink-0">
    <Button ref={anchor} data-calendar-trigger type="button" variant="secondary" className="h-11 max-w-[calc(100vw-152px)] sm:max-w-72 justify-between gap-2 px-3" aria-haspopup="dialog" aria-expanded={open} data-testid="calendar-period-picker" onClick={() => setOpen(current => !current)}>
      <span className="truncate text-left">{periodLabel || formatPickerDate(value, locale)}</span><CalendarDays size={18} className="shrink-0" />
    </Button>
    {open && <DatePickerPanel testId="calendar-date-picker" anchor={anchor} label={t("calendar.selectedDay")} range={false}
      value={{ from: value, to: value }} today={todayValue} yearRange={yearRange} onApply={next => { onChange(next.from); close(); }} onClose={close} />}
  </div>;
}

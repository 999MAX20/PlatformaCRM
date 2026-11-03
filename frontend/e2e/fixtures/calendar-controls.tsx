import { StrictMode, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { useForm } from "react-hook-form";
import { I18nProvider, useI18n } from "../../src/lib/i18n";
import { Input } from "../../src/components/ui/Input";
import { Button } from "../../src/components/ui/Button";
import { Dialog } from "../../src/components/ui/Overlay";
import { DateRangePicker, DatePickerPanel } from "../../src/components/ui/DateRangePicker";
import { CalendarPicker } from "../../src/features/calendar/components/CalendarPicker";
import { RecordsPeriodPanel } from "../../src/features/calendar/RecordsPeriodPanel";
import { CrmFilterFields } from "../../src/components/crm/CrmFilterFields";
import { crmFilterDefaults } from "../../src/components/crm/useCrmFilters";
import "@fontsource-variable/manrope";
import "../../src/styles.css";

function Fixture() {
  const { t, language, setLanguage } = useI18n();
  const [day, setDay] = useState("2026-11-04");
  const [dateTime, setDateTime] = useState("2026-11-04T14:35");
  const [range, setRange] = useState({ from: "2026-11-04", to: "2026-11-05" });
  const [kind, setKind] = useState<"records" | "operations" | null>(null);
  const [dialog, setDialog] = useState(false);
  const [filters, setFilters] = useState(crmFilterDefaults("clients"));
  const [submitted, setSubmitted] = useState("");
  const period = useRef<HTMLButtonElement>(null);
  const operations = useRef<HTMLButtonElement>(null);
  const form = useForm({ defaultValues: { date: "2026-11-04" } });
  const close = (restore = true) => { (kind === "records" ? period : operations).current?.focus({ preventScroll: true }); setKind(null); if (!restore) (document.activeElement as HTMLElement)?.blur(); };
  return <main className="mx-auto max-w-3xl space-y-4 p-4">
    <nav>{(["ru", "kk", "en"] as const).map(value => <Button key={value} type="button" onClick={() => setLanguage(value)}>{value}</Button>)}</nav>
    <h1>Calendar controls</h1>
    <div data-testid="day"><Input label={t("appointment.date")} type="date" value={day} min="2026-11-02" max="2026-12-05" onChange={e => setDay(e.target.value)} /></div>
    <output data-testid="day-value">{day}</output>
    <div data-testid="datetime"><Input label={t("tasks.dueAt")} type="datetime-local" value={dateTime} min="2026-11-01T10:00" max="2026-11-10T18:00" onChange={e => setDateTime(e.target.value)} /></div>
    <output data-testid="datetime-value">{dateTime}</output>
    <div data-testid="disabled"><Input type="date" label="Disabled date" value={day} disabled /></div>
    <div data-testid="readonly"><Input type="date" label="Readonly date" value={day} readOnly /></div>
    <div data-testid="date-error"><Input type="date" label="Invalid date" value="" onChange={() => undefined} error={t("crmFilters.invalidDate")} /></div>
    <DateRangePicker label="Range" value={range} onChange={setRange} today="2026-11-03" />
    <output data-testid="range-value">{range.from}/{range.to}</output>
    <Button ref={period} type="button" data-testid="records-trigger" onClick={() => setKind("records")}>Records</Button>
    {kind === "records" && <RecordsPeriodPanel anchor={period} {...range} today="2026-11-03" onClose={close} onApply={next => { setRange(next); close(); }} />}
    <Button ref={operations} type="button" data-testid="operations-trigger" onClick={() => setKind("operations")}>Operations</Button>
    {kind === "operations" && <DatePickerPanel anchor={operations} label="Operations" value={range} today="2026-11-10" max="2026-11-10" validate={next => (Date.parse(next.to) - Date.parse(next.from)) / 86400000 <= 365} onClose={close} onApply={next => { setRange(next); close(); }} />}
    <CalendarPicker value={day} onChange={setDay} locale={language} todayValue="2026-11-03" />
    <Button type="button" onClick={() => setDialog(true)}>Open form</Button>
    <Dialog title="Form" open={dialog} onClose={() => setDialog(false)}>
      <form onSubmit={form.handleSubmit(values => setSubmitted(values.date))}>
        <Input type="date" label="Registered date" required min="2026-11-02" max="2026-12-05" {...form.register("date", { required: true })} />
        <Button type="submit">Submit</Button>
        <Button type="button" onClick={() => form.reset({ date: "2026-11-06" })}>Reset date</Button>
      </form>
      <CrmFilterFields kind="clients" value={filters} onChange={patch => setFilters(current => ({ ...current, ...patch }))} options={{}} today="2026-11-03" />
      <output data-testid="filters">{filters.created_from}/{filters.created_to}</output>
    </Dialog>
    <output data-testid="submitted">{submitted}</output>
    <Button type="button" data-testid="outside">Outside</Button>
  </main>;
}
createRoot(document.getElementById("root")!).render(<StrictMode><I18nProvider><Fixture /></I18nProvider></StrictMode>);

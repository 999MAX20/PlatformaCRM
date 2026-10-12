import { useState } from "react";
import { useSearchParams } from "react-router";
import { branchesApi, type Branch, type BranchConfiguration, type Interval } from "../../../api/branches";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import { useI18n } from "../../../lib/i18n";

export function BranchScheduleEditor({ tab, branch, branches, config, save, disabled }: {
  tab: string; branch: Branch; branches: Branch[]; config: BranchConfiguration;
  save: (operation: () => Promise<unknown>) => Promise<unknown>; disabled: boolean;
}) {
  const { t, language } = useI18n();
  const [params] = useSearchParams();
  const initialResource = config.assignments.some((item) => String(item.resource) === params.get("resource")) ? params.get("resource")! : "";
  const [resource, setResource] = useState(initialResource);
  const [weekday, setWeekday] = useState(0);
  const [date, setDate] = useState("");
  const [dated, setDated] = useState(false);
  const [intervals, setIntervals] = useState<Interval[]>(config.days.find((day) => day.resource === (initialResource ? Number(initialResource) : null) && day.weekday === 0)?.intervals || []);
  const [other, setOther] = useState("");
  const [minutes, setMinutes] = useState("30");
  const week = Array.from({ length: 7 }, (_, index) => ({ value: index, label: new Date(2026, 9, 5 + index).toLocaleDateString(language, { weekday: "long" }) }));
  const load = (staff: string, day: number, target: string, isDated: boolean) => {
    setResource(staff); setWeekday(day); setDate(target); setDated(isDated);
    setIntervals(config.days.find((item) => item.resource === (staff ? Number(staff) : null) && (isDated ? item.date === target : !item.date && item.weekday === day))?.intervals || []);
  };
  const payload = { resource: resource ? Number(resource) : null, ...(dated ? { date } : { weekday }), intervals };
  return <form className="space-y-4 rounded-card border border-platforma-border bg-surface-card p-4" onSubmit={(event) => { event.preventDefault(); void save(() => tab === "travel" ? branchesApi.travel(branch.id, { other_branch: Number(other), minutes: Number(minutes) }) : branchesApi.day(branch.id, payload)).catch(() => undefined); }}>
    <fieldset disabled={disabled} className="space-y-4">
      {tab === "travel" ? <>
        <Select label={t("branches.branch")} value={other} onChange={(event) => { const id = Number(event.target.value); setOther(event.target.value); setMinutes(String(config.travel.find((item) => item.from_branch === id || item.to_branch === id)?.minutes ?? 30)); }} options={[{ value: "", label: t("branches.choose") }, ...branches.filter((item) => item.id !== branch.id && !item.archived_at).map((item) => ({ value: item.id, label: item.name }))]} />
        <Input label={t("branches.travelMinutes")} type="number" min={0} max={1440} value={minutes} onChange={(event) => setMinutes(event.target.value)} required />
      </> : <>
        <Select label={t("branches.scheduleFor")} value={resource} onChange={(event) => load(event.target.value, weekday, date, dated)} options={[{ value: "", label: t("branches.openingHours") }, ...config.assignments.filter((item) => item.is_active).map((item) => ({ value: item.resource, label: item.resource_name }))]} />
        <label className="flex min-h-10 items-center gap-2 text-sm"><input type="checkbox" checked={dated} onChange={(event) => load(resource, weekday, date, event.target.checked)} />{t("branches.dateOverride")}</label>
        {dated ? <Input label={t("appointment.date")} type="date" required value={date} onChange={(event) => load(resource, weekday, event.target.value, true)} /> : <Select label={t("branches.weekday")} value={weekday} options={week} onChange={(event) => load(resource, Number(event.target.value), date, false)} />}
        {intervals.map((interval, index) => <div key={index} className="grid grid-cols-[1fr_1fr_auto] items-end gap-2">
          <Input label={t("branches.start")} type="time" value={interval.start} required onChange={(event) => setIntervals(intervals.map((item, i) => i === index ? { ...item, start: event.target.value } : item))} />
          <Input label={t("branches.end")} type="time" value={interval.end} required onChange={(event) => setIntervals(intervals.map((item, i) => i === index ? { ...item, end: event.target.value } : item))} />
          <Button type="button" variant="secondary" aria-label={t("branches.removeInterval")} onClick={() => setIntervals(intervals.filter((_, i) => i !== index))}>−</Button>
        </div>)}
        {!intervals.length && <p className="text-sm text-platforma-subtle">{t("branches.dayOff")}</p>}
        <Button type="button" variant="secondary" onClick={() => setIntervals([...intervals, { start: "09:00", end: "18:00" }])}>{t("branches.addInterval")}</Button>
      </>}
      <div className="flex flex-wrap gap-2"><Button type="submit" disabled={disabled || (tab === "travel" ? !other : dated && !date)}>{t("common.save")}</Button>
        {tab === "schedule" && dated && date && <Button type="button" variant="secondary" onClick={() => { void save(() => branchesApi.day(branch.id, { ...payload, remove: true })).then(() => load(resource, weekday, "", false)).catch(() => undefined); }}>{t("branches.removeOverride")}</Button>}
      </div>
    </fieldset>
  </form>;
}

import { DraftGuard } from "../../../components/actions/DraftGuard";
import { useActionConfirm } from "../../../components/actions/ActionConfirmProvider";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router";
import { branchesApi, type Branch, type BranchConfiguration, type Interval } from "../../../api/branches";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import { useI18n } from "../../../lib/i18n";

export function BranchScheduleEditor({ tab, branch, branches, config, save, disabled, onDirtyChange }: {
  tab: string; branch: Branch; branches: Branch[]; config: BranchConfiguration;
  save: (operation: () => Promise<unknown>) => Promise<unknown>; disabled: boolean;
  onDirtyChange?: (dirty: boolean) => void;
}) {
  const { t } = useI18n();
  const confirm = useActionConfirm();
  const [dirty, setDirty] = useState(false);
  useEffect(() => { onDirtyChange?.(dirty); return () => onDirtyChange?.(false); }, [dirty, onDirtyChange]);
  const [params] = useSearchParams();
  const targets = [...config.assignments.filter(item => item.is_active).map(item => ({ value: item.resource, label: item.resource_name })),
    ...(config.physical_resources || []).filter(item => item.is_active).map(item => ({ value: item.id, label: item.name }))];
  const initialResource = targets.some(item => String(item.value) === params.get("resource")) ? params.get("resource")! : "";
  const [resource, setResource] = useState(initialResource);
  const [weekday, setWeekday] = useState(0);
  const [date, setDate] = useState("");
  const [dated, setDated] = useState(false);
  const [intervals, setIntervals] = useState<Interval[]>(config.days.find((day) => day.resource === (initialResource ? Number(initialResource) : null) && day.weekday === 0)?.intervals || []);
  const [other, setOther] = useState("");
  const [minutes, setMinutes] = useState("30");
  const week = Array.from({ length: 7 }, (_, index) => ({ value: index, label: t(["weekday.mon", "weekday.tue", "weekday.wed", "weekday.thu", "weekday.fri", "weekday.sat", "weekday.sun"][index]) }));
  const load = async (staff: string, day: number, target: string, isDated: boolean) => {
    if (dirty && !(await confirm({ title: t("workingHours.discardChanges"), confirmLabel: t("actions.discardChanges"), tone: "warning" })).confirmed) return;
    setDirty(false);
    setResource(staff); setWeekday(day); setDate(target); setDated(isDated);
    setIntervals(config.days.find((item) => item.resource === (staff ? Number(staff) : null) && (isDated ? item.date === target : !item.date && item.weekday === day))?.intervals || []);
  };
  const payload = { resource: resource ? Number(resource) : null, ...(dated ? { date } : { weekday }), intervals };
  return <form className="space-y-4 rounded-card border border-platforma-border bg-surface-card p-4" onSubmit={(event) => { event.preventDefault(); void save(() => tab === "travel" ? branchesApi.travel(branch.id, { other_branch: Number(other), minutes: Number(minutes) }) : branchesApi.day(branch.id, payload)).then(() => setDirty(false)).catch(() => undefined); }}>
    <DraftGuard dirty={dirty} pending={disabled && dirty} />
    <fieldset disabled={disabled} className="space-y-4">
      {tab === "travel" ? <>
        <Select label={t("branches.branch")} value={other} onChange={async (event) => { const value = event.target.value; const id = Number(value); if (dirty && !(await confirm({ title: t("workingHours.discardChanges"), confirmLabel: t("actions.discardChanges"), tone: "warning" })).confirmed) return; setDirty(false); setOther(value); setMinutes(String(config.travel.find((item) => item.from_branch === id || item.to_branch === id)?.minutes ?? 30)); }} options={[{ value: "", label: t("branches.choose") }, ...branches.filter((item) => item.id !== branch.id && !item.archived_at).map((item) => ({ value: item.id, label: item.name }))]} />
        <Input label={t("branches.travelMinutes")} type="number" min={0} max={1440} value={minutes} onChange={(event) => { setDirty(true); setMinutes(event.target.value); }} required />
      </> : <>
        <Select label={t("branches.scheduleFor")} value={resource} onChange={(event) => load(event.target.value, weekday, date, dated)} options={[{ value: "", label: t("branches.openingHours") }, ...targets]} />
        <label className="flex min-h-10 items-center gap-2 text-sm"><input type="checkbox" checked={dated} onChange={(event) => load(resource, weekday, date, event.target.checked)} />{t("branches.dateOverride")}</label>
        {dated ? <Input label={t("appointment.date")} type="date" required value={date} onChange={(event) => load(resource, weekday, event.target.value, true)} /> : <Select label={t("branches.weekday")} value={weekday} options={week} onChange={(event) => load(resource, Number(event.target.value), date, false)} />}
        {intervals.map((interval, index) => <div key={index} className="grid grid-cols-[1fr_1fr_auto] items-end gap-2">
          <Input label={t("branches.start")} type="time" value={interval.start} required onChange={(event) => { setDirty(true); setIntervals(intervals.map((item, i) => i === index ? { ...item, start: event.target.value } : item)); }} />
          <Input label={t("branches.end")} type="time" value={interval.end} required onChange={(event) => { setDirty(true); setIntervals(intervals.map((item, i) => i === index ? { ...item, end: event.target.value } : item)); }} />
          <Button type="button" variant="secondary" aria-label={t("branches.removeInterval")} onClick={() => { setDirty(true); setIntervals(intervals.filter((_, i) => i !== index)); }}>−</Button>
        </div>)}
        {!intervals.length && <p className="text-sm text-platforma-subtle">{t("branches.dayOff")}</p>}
        <Button type="button" variant="secondary" onClick={() => { setDirty(true); setIntervals([...intervals, { start: "09:00", end: "18:00" }]); }}>{t("branches.addInterval")}</Button>
      </>}
      <div className="flex flex-wrap gap-2"><Button type="submit" disabled={disabled || (tab === "travel" ? !other : dated && !date)}>{t("common.save")}</Button>
        {tab === "schedule" && dated && date && <Button type="button" variant="secondary" onClick={() => { void save(() => branchesApi.day(branch.id, { ...payload, remove: true })).then(() => { setDirty(false); setDate(""); setDated(false); setIntervals(config.days.find(day => day.resource === (resource ? Number(resource) : null) && !day.date && day.weekday === weekday)?.intervals || []); }).catch(() => undefined); }}>{t("branches.removeOverride")}</Button>}
      </div>
    </fieldset>
  </form>;
}

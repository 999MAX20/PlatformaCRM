import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";
import { branchesApi, type Branch, type BranchConfiguration, type Interval } from "../../../api/branches";
import { scheduleExceptionsApi, workingHoursApi } from "../../../api/workingHours";
import { useActionConfirm } from "../../../components/actions/ActionConfirmProvider";
import { DraftGuard } from "../../../components/actions/DraftGuard";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Modal } from "../../../components/ui/Modal";
import { Select } from "../../../components/ui/Select";
import { ErrorState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import type { ScheduleException, WorkingHours } from "../../../types";
import type { ScheduleTarget } from "../BusinessSchedulePage";
import { scheduleCell, weekdayKeys, weekdayOf } from "../schedule";

export function ScheduleDayDialog({ branch, target, targets, date, weekly, config, hours, exceptions, onClose }: {
  branch: Branch; target: ScheduleTarget; targets: ScheduleTarget[]; date: string; weekly: boolean;
  config: BranchConfiguration; hours: WorkingHours[]; exceptions: ScheduleException[]; onClose: () => void;
}) {
  const { t } = useI18n();
  const confirm = useActionConfirm();
  const cache = useQueryClient();
  const automatic = !!branch.uses_business_defaults;
  const [selectedTarget, setSelectedTarget] = useState(target);
  const [isWeekly, setIsWeekly] = useState(weekly);
  const [days, setDays] = useState([weekdayOf(date)]);
  const [effectiveFrom, setEffectiveFrom] = useState(date);
  const [dirty, setDirty] = useState(false);
  const resolve = (next: ScheduleTarget, asWeek: boolean) => scheduleCell({ automatic, config: asWeek ? { ...config, days: config.days.filter(row => !row.date) } : config,
    hours, exceptions: asWeek ? [] : exceptions, resource: next.id, date });
  const [intervals, setIntervals] = useState<Interval[]>(resolve(target, weekly).intervals);
  const current = resolve(selectedTarget, isWeekly);
  const canManage = branch.can_manage && !branch.archived_at;
  const mutation = useMutation({
    mutationFn: async (remove: boolean) => {
      if (!automatic) {
        if (isWeekly) return branchesApi.weekdays(branch.id, { resource: selectedTarget.id, weekdays: days, intervals, effective_from: effectiveFrom });
        return branchesApi.day(branch.id, { resource: selectedTarget.id, date, intervals, remove });
      }
      const times = { start_time: intervals[0]?.start || "09:00", end_time: intervals[0]?.end || "18:00", is_day_off: !intervals.length };
      if (isWeekly) return workingHoursApi.bulkUpsertWeek({ business: branch.business, resource: selectedTarget.id, days: days.map(weekday => ({ weekday, ...times })) });
      if (selectedTarget.id === null) throw new Error(t("business.automaticOpeningWeek"));
      const existing = exceptions.find(row => row.resource === selectedTarget.id && row.date === date);
      if (remove) return existing ? scheduleExceptionsApi.remove(existing.id) : undefined;
      const payload = { business: branch.business, resource: selectedTarget.id, date, ...times };
      return existing ? scheduleExceptionsApi.update({ id: existing.id, payload }) : scheduleExceptionsApi.create(payload);
    },
    onSuccess: async () => {
      setDirty(false);
      await Promise.all(["working-hours", "schedule-exceptions", "branch-configuration", "branch-catalog", "available-slots", "branches"].map(key => cache.invalidateQueries({ queryKey: [key] })));
      onClose();
    },
  });
  async function changeTarget(next: ScheduleTarget, nextWeekly: boolean) {
    if (dirty && !(await confirm({ title: t("workingHours.discardChanges"), confirmLabel: t("actions.discardChanges"), tone: "warning" })).confirmed) return;
    setSelectedTarget(next); setIsWeekly(nextWeekly); setIntervals(resolve(next, nextWeekly).intervals); setDays([weekdayOf(date)]); setDirty(false);
  }
  async function close() {
    if (mutation.isPending) return;
    if (dirty && !(await confirm({ title: t("workingHours.discardChanges"), confirmLabel: t("actions.discardChanges"), tone: "warning" })).confirmed) return;
    onClose();
  }
  const sorted = [...intervals].sort((left, right) => left.start.localeCompare(right.start));
  const invalid = sorted.some(interval => !interval.start || !interval.end || interval.start >= interval.end)
    || sorted.some((interval, index) => index > 0 && sorted[index - 1].end > interval.start);
  return <Modal title={`${selectedTarget.name} · ${isWeekly ? t("workingHours.weekTitle") : date}`} open onClose={() => void close()} closeOnBackdrop={!mutation.isPending}>
    <DraftGuard dirty={dirty} pending={mutation.isPending} />
    <form className="space-y-4" onSubmit={event => { event.preventDefault(); mutation.mutate(false); }}>
      {mutation.error && <ErrorState error={mutation.error} />}
      <Select label={t("branches.scheduleFor")} value={selectedTarget.id ?? "opening"} disabled={mutation.isPending}
        options={targets.map(item => ({ value: item.id ?? "opening", label: item.name }))}
        onChange={event => { const next = targets.find(item => String(item.id ?? "opening") === event.target.value); if (next) void changeTarget(next, automatic && next.id === null ? true : isWeekly); }} />
      {automatic && selectedTarget.id === null ? <p className="text-sm text-platforma-subtle">{t("business.automaticOpeningWeek")}</p> : <Select label={t("nav.workingHours")} value={isWeekly ? "weekly" : "date"} disabled={mutation.isPending}
        options={[{ value: "date", label: t("branches.dateOverride") }, { value: "weekly", label: t("workingHours.weekTitle") }]}
        onChange={event => void changeTarget(selectedTarget, event.target.value === "weekly")} />}
      <fieldset disabled={!canManage || mutation.isPending} className="space-y-4">
        {isWeekly && !automatic && <Input label={t("management.effectiveFrom")} type="date" required value={effectiveFrom} onChange={event => { setEffectiveFrom(event.target.value); setDirty(true); }} />}
        {isWeekly && <fieldset className="flex flex-wrap gap-2"><legend className="mb-2 text-sm font-semibold">{t("branches.weekday")}</legend>
          {weekdayKeys.map((key, weekday) => <label key={key} className="flex min-h-11 items-center gap-2 rounded-control border border-platforma-border px-3 text-sm"><input type="checkbox" checked={days.includes(weekday)} onChange={event => { setDirty(true); setDays(event.target.checked ? [...days, weekday] : days.filter(day => day !== weekday)); }} />{t(key)}</label>)}
        </fieldset>}
        {intervals.map((interval, index) => <div key={index} className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] items-end gap-2">
          <Input label={t("branches.start")} type="time" required value={interval.start} onChange={event => { setDirty(true); setIntervals(intervals.map((item, i) => i === index ? { ...item, start: event.target.value } : item)); }} />
          <Input label={t("branches.end")} type="time" required value={interval.end} onChange={event => { setDirty(true); setIntervals(intervals.map((item, i) => i === index ? { ...item, end: event.target.value } : item)); }} />
          <Button type="button" variant="secondary" aria-label={t("branches.removeInterval")} onClick={() => { setDirty(true); setIntervals(intervals.filter((_, i) => i !== index)); }}>−</Button>
        </div>)}
        {!intervals.length && <p className="text-sm text-platforma-subtle">{t("workingHours.dayOff")}</p>}
        {(!automatic || !intervals.length) && <Button type="button" variant="secondary" disabled={intervals.length >= 24} onClick={() => { setDirty(true); setIntervals([...intervals, { start: "09:00", end: "18:00" }]); }}>{t("branches.addInterval")}</Button>}
        {invalid && <p role="alert" className="text-sm text-platforma-danger">{t("business.invalidIntervals")}</p>}
        <div className="flex flex-wrap gap-2">
          <Button type="submit" isLoading={mutation.isPending} disabled={invalid || (isWeekly && !days.length)}>{t("common.save")}</Button>
          {!isWeekly && current.override && <Button type="button" variant="secondary" onClick={async () => {
            if (dirty && !(await confirm({ title: t("workingHours.discardChanges"), confirmLabel: t("actions.discardChanges"), tone: "warning" })).confirmed) return;
            mutation.mutate(true);
          }}>{t("branches.removeOverride")}</Button>}
        </div>
      </fieldset>
      {selectedTarget.kind === "staff" && <Link className="platforma-focus-ring inline-flex min-h-11 items-center text-sm text-brand-700 underline" to={`/app/business/staff?branch=${branch.id}&resource=${selectedTarget.id}&absence=1`}>{t("branches.absences")}</Link>}
      <Button type="button" variant="secondary" disabled={mutation.isPending} onClick={() => void close()}>{t("common.close")}</Button>
    </form>
  </Modal>;
}

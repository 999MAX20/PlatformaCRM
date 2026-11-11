import type { BranchConfiguration, Interval } from "../../api/branches";
import type { Id, ScheduleException, WorkingHours } from "../../types";

export const weekdayKeys = ["weekday.monShort", "weekday.tueShort", "weekday.wedShort", "weekday.thuShort", "weekday.friShort", "weekday.satShort", "weekday.sunShort"];

export function shiftDate(date: string, days: number) {
  const value = new Date(`${date}T12:00:00Z`);
  value.setUTCDate(value.getUTCDate() + days);
  return value.toISOString().slice(0, 10);
}

export function weekdayOf(date: string) {
  return (new Date(`${date}T12:00:00Z`).getUTCDay() + 6) % 7;
}

export function weekDates(date: string) {
  const monday = shiftDate(date, -weekdayOf(date));
  return Array.from({ length: 7 }, (_, day) => shiftDate(monday, day));
}

export function validDate(value: string | null, fallback: string) {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return fallback;
  const date = new Date(`${value}T12:00:00Z`);
  return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value ? value : fallback;
}

export function scheduleCell({ automatic, config, hours, exceptions, resource, date }: {
  automatic: boolean; config: BranchConfiguration; hours: WorkingHours[]; exceptions: ScheduleException[]; resource: Id | null; date: string;
}): { intervals: Interval[]; override: boolean; configured: boolean; absent: boolean } {
  const weekday = weekdayOf(date);
  const absent = resource !== null && !!config.absences?.some(row => row.resource_id === resource && row.starts_on <= date && row.ends_on >= date);
  if (automatic) {
    const exception = resource === null ? undefined : exceptions.find(row => row.resource === resource && row.date === date);
    const regular = hours.find(row => row.resource === resource && row.weekday === weekday)
      || hours.find(row => row.resource === null && row.weekday === weekday);
    const row = exception || regular;
    return { intervals: row && !row.is_day_off ? [{ start: row.start_time.slice(0, 5), end: row.end_time.slice(0, 5) }] : [], override: !!exception, configured: !!row, absent };
  }
  const override = config.days.find(row => row.resource === resource && row.date === date);
  const row = override || config.days.filter(row => row.resource === resource && row.date === null && row.weekday === weekday && (!row.effective_from || row.effective_from <= date))
    .sort((a, b) => (b.effective_from || "0001-01-01").localeCompare(a.effective_from || "0001-01-01"))[0];
  return { intervals: row?.intervals || [], override: !!override, configured: !!row, absent };
}

import type { BranchCatalog, Interval } from "../../api/branches";
import type { Id } from "../../types";

export function branchIntervals(catalog: BranchCatalog | undefined, date: string, resource: Id | null): Interval[] {
  const weekday = (new Date(`${date}T12:00:00`).getDay() + 6) % 7;
  const forResource = (id: Id | null) => {
    const rows = catalog?.days?.filter((row) => row.resource === id) || [];
    return (rows.find((row) => row.date === date) || rows.find((row) => !row.date && row.weekday === weekday))?.intervals || [];
  };
  const opening = forResource(null);
  if (!resource) return opening;
  if (catalog?.absences?.some((item) => item.resource_id === resource && item.starts_on <= date && item.ends_on >= date)) return [];
  return opening.flatMap((left) => forResource(resource).flatMap((right) => {
    const start = left.start > right.start ? left.start : right.start;
    const end = left.end < right.end ? left.end : right.end;
    return start < end ? [{ start, end }] : [];
  }));
}

export function branchWorking(catalog: BranchCatalog | undefined, date: string, hour: number, resource: Id | null) {
  const minutes = (value: string) => { const [h, m] = value.split(":").map(Number); return h * 60 + m; };
  return branchIntervals(catalog, date, resource).some((interval) => minutes(interval.start) < (hour + 1) * 60 && minutes(interval.end) > hour * 60);
}

export type CalendarYearRange = { from: number; to: number };

export function calendarYears(today: string, visibleYear: number, selected: string[], bounds?: CalendarYearRange, min?: string, max?: string) {
  const current = Number(today.slice(0, 4));
  const anchors = [visibleYear, current, ...selected.filter(value => /^\d{4}-\d{2}-\d{2}$/.test(value)).map(value => Number(value.slice(0, 4)))];
  const first = Math.max(1, min ? Number(min.slice(0, 4)) : Math.min(bounds?.from ?? current - 5, ...anchors));
  const last = Math.min(9999, max ? Number(max.slice(0, 4)) : Math.max(bounds?.to ?? current + 5, ...anchors));
  return Array.from({ length: Math.max(0, last - first + 1) }, (_, index) => first + index);
}

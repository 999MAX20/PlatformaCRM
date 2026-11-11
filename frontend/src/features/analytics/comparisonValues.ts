export function comparisonChange(current: number | null, previous: number | null) {
  if (current === null || previous === null) return null;
  return {
    absolute: Math.round((current - previous) * 10) / 10,
    percent: previous > 0 ? Math.round((current - previous) / previous * 1000) / 10 : null,
  };
}

export function includePreviousGroups<T>(current: T[], previous: T[], key: (row: T) => string | number, empty: (row: T) => T): T[] {
  const keys = new Set(current.map(key));
  return [...current, ...previous.filter(row => !keys.has(key(row))).map(empty)];
}

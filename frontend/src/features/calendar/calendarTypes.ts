export type CalendarViewMode = "week" | "month";

export type CalendarResource = {
  id: number | null;
  name: string;
};

export type SearchableCalendarFilterOption = {
  value: string;
  label: string;
};

export type CalendarTranslate = (key: string, values?: Record<string, string | number>) => string;

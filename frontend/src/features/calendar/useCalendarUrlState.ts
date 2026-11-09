import { useCallback, useEffect, useMemo, type SetStateAction } from "react";
import { useSearchParams } from "react-router";
import { todayInTimeZone } from "../../lib/format";
import { useActiveBusiness } from "../../hooks/useBusiness";
import type { CalendarViewMode } from "./calendarTypes";
import { getCalendarRange, getQueryDate, getQueryView, normalizeTimeZone } from "./calendarUtils";

type Args = { business: ReturnType<typeof useActiveBusiness>["business"] };
export function useCalendarUrlState({ business }: Args) {
  const [searchParams, setSearchParams] = useSearchParams();
  const businessTimeZone = normalizeTimeZone(business?.timezone || "Asia/Almaty");
  const fallbackToday = todayInTimeZone(businessTimeZone);
  const periodDate = getQueryDate(searchParams.get("date"), fallbackToday);
  const date = getQueryDate(searchParams.get("day"), periodDate);
  const viewMode = getQueryView(searchParams.get("view"));
  const branchFilter = searchParams.get("branch") || "";
  const serviceFilter = searchParams.get("service") || "";
  const resourceFilter = searchParams.get("resource") || "";
  const statusFilter = searchParams.get("status") || "";
  const appointmentIdFromUrl = Number(searchParams.get("appointment")) || null;
  const calendarRange = useMemo(() => getCalendarRange(periodDate, viewMode), [periodDate, viewMode]);
  const updateCalendar = useCallback((patch: Record<string, string>) => {
    setSearchParams(current => {
      const next = new URLSearchParams(current);
      for (const [key, value] of Object.entries(patch)) {
        if (value) next.set(key, value); else next.delete(key);
      }
      next.delete("search");
      if ("date" in patch && !("day" in patch)) next.delete("day");
      return next;
    });
  }, [setSearchParams]);
  const setDate = useCallback((value: SetStateAction<string>) => {
    const next = typeof value === "function" ? value(date) : value;
    if (next !== periodDate || searchParams.has("day")) updateCalendar({ date: next });
  }, [date, periodDate, searchParams, updateCalendar]);
  const setViewMode = (value: CalendarViewMode) => updateCalendar({ view: value, day: "", appointment: "" });
  useEffect(() => {
    if (searchParams.get("date") === periodDate && searchParams.get("view") === viewMode && !searchParams.has("search")) return;
    setSearchParams(current => {
      const next = new URLSearchParams(current);
      next.set("date", periodDate);
      next.set("view", viewMode);
      next.delete("search");
      return next;
    }, { replace: true });
  }, [periodDate, viewMode, searchParams, setSearchParams]);
  return { searchParams, setSearchParams, updateCalendar, branchFilter, fallbackToday,
    date, periodDate, setDate, viewMode, setViewMode, serviceFilter, resourceFilter, statusFilter,
    appointmentIdFromUrl, calendarRange, businessTimeZone };
}

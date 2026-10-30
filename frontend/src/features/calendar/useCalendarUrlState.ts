import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router";

import { todayInTimeZone } from "../../lib/format";

import { useActiveBusiness } from "../../hooks/useBusiness";

import type { CalendarViewMode } from "./calendarTypes";
import {
  getCalendarRange,
  getQueryDate,
  getQueryView,
  isDateValue,
  normalizeTimeZone,
} from "./calendarUtils";

type Args = { business: ReturnType<typeof useActiveBusiness>["business"] };
export function useCalendarUrlState({ business }: Args) {
  const [searchParams, setSearchParams] = useSearchParams();
  const branchFilter = searchParams.get("branch") || "";
  const fallbackToday = todayInTimeZone(
    normalizeTimeZone(business?.timezone || "Asia/Almaty"),
  );
  const [date, setDate] = useState(() =>
    getQueryDate(searchParams.get("date"), fallbackToday),
  );
  const [viewMode, setViewMode] = useState<CalendarViewMode>(() =>
    getQueryView(searchParams.get("view")),
  );
  const [serviceFilter, setServiceFilter] = useState(
    searchParams.get("service") || "",
  );
  const [resourceFilter, setResourceFilter] = useState(
    searchParams.get("resource") || "",
  );
  const [statusFilter, setStatusFilter] = useState(
    searchParams.get("status") || "",
  );
  const [search, setSearch] = useState(searchParams.get("search") || "");
  const appointmentIdFromUrl = Number(searchParams.get("appointment")) || null;
  const searchParamsKey = searchParams.toString();
  const calendarRange = useMemo(
    () => getCalendarRange(date, viewMode),
    [date, viewMode],
  );
  const businessTimeZone = normalizeTimeZone(
    business?.timezone || "Asia/Almaty",
  );
  useEffect(() => {
    const params = new URLSearchParams(searchParamsKey);
    const nextDate = params.get("date");
    const nextView = params.get("view");
    const nextService = params.get("service") || "";
    const nextResource = params.get("resource") || "";
    const nextStatus = params.get("status") || "";
    const nextSearch = params.get("search") || "";

    if (isDateValue(nextDate)) setDate(nextDate!);
    if (nextView) setViewMode(getQueryView(nextView));
    setServiceFilter(nextService);
    setResourceFilter(nextResource);
    setStatusFilter(nextStatus);
    setSearch(nextSearch);
  }, [searchParamsKey]);
  useEffect(() => {
    setSearchParams(
      (current) => {
        const next = new URLSearchParams(current);
        next.set("date", date);
        next.set("view", viewMode);
        if (serviceFilter) next.set("service", serviceFilter);
        else next.delete("service");
        if (resourceFilter) next.set("resource", resourceFilter);
        else next.delete("resource");
        if (statusFilter) next.set("status", statusFilter);
        else next.delete("status");
        if (search.trim()) next.set("search", search.trim());
        else next.delete("search");
        if (next.toString() === current.toString()) return current;
        return next;
      },
      { replace: true },
    );
  }, [
    date,
    resourceFilter,
    search,
    serviceFilter,
    setSearchParams,
    statusFilter,
    viewMode,
  ]);
  return {
    searchParams,
    setSearchParams,
    branchFilter,
    fallbackToday,
    date,
    setDate,
    viewMode,
    setViewMode,
    serviceFilter,
    setServiceFilter,
    resourceFilter,
    setResourceFilter,
    statusFilter,
    setStatusFilter,
    search,
    setSearch,
    appointmentIdFromUrl,
    searchParamsKey,
    calendarRange,
    businessTimeZone,
  };
}

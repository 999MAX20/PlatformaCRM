import { useQuery } from "@tanstack/react-query";
import { appointmentsApi } from "../../api/appointments";

import { branchesApi } from "../../api/branches";

import { scheduleExceptionsApi } from "../../api/workingHours";

import { useActiveBusiness } from "../../hooks/useBusiness";

import { tasksApi } from "../../api/tasks";
import { taskDateISO } from "../tasks/workspaceUtils";

import type { Appointment } from "../../types";

import { getCalendarRange, shiftDateValue } from "./calendarUtils";
import type { CalendarViewMode } from "./calendarTypes";

type Args = {
  business: ReturnType<typeof useActiveBusiness>["business"];
  userId: number | undefined;
  canViewTasks: boolean;
  calendarRange: ReturnType<typeof getCalendarRange>;
  viewMode: CalendarViewMode;
  inspectorOpen: boolean;
  businessTimeZone: string;
  branchFilter: string;
  serviceFilter: string;
  resourceFilter: string;
  statusFilter: string;
  date: string;
  appointmentIdFromUrl: number | null;
};
export function useCalendarQueries({
  business,
  userId,
  canViewTasks,
  calendarRange,
  viewMode,
  inspectorOpen,
  businessTimeZone,
  branchFilter,
  serviceFilter,
  resourceFilter,
  statusFilter,
  date,
  appointmentIdFromUrl,
}: Args) {
  const detailRange = viewMode === "year" ? { start: date, end: shiftDateValue(date, 1) } : calendarRange;
  const detailsEnabled = viewMode !== "year" || inspectorOpen || !!appointmentIdFromUrl;
  const branchesQuery = useQuery({
    queryKey: ["branches", business?.id],
    queryFn: () => branchesApi.listAll({ business: business!.id }),
    enabled: !!business,
  });
  const hasBranches = !!branchesQuery.data?.length;
  const soleBranch = branchesQuery.data?.length === 1 ? branchesQuery.data[0] : undefined;
  const scheduleBranch = branchFilter || (soleBranch ? String(soleBranch.id) : "");
  const branchCatalog = useQuery({
    queryKey: ["branch-catalog", Number(scheduleBranch)],
    queryFn: () => branchesApi.catalog(Number(scheduleBranch)),
    enabled: !!scheduleBranch,
  });
  const tasks = useQuery({
    queryKey: [
      "tasks",
      "calendar",
      business?.id,
      userId,
      detailRange.start,
      detailRange.end,
      businessTimeZone,
    ],
    queryFn: () =>
      tasksApi.listAll({
        business: business!.id,
        status: "active",
        due_from: taskDateISO(`${detailRange.start}T00:00`, businessTimeZone),
        due_to: new Date(
          Date.parse(
            taskDateISO(`${detailRange.end}T00:00`, businessTimeZone)!,
          ) - 1,
        ).toISOString(),
      }),
    enabled: !!business?.id && canViewTasks && detailsEnabled,
  });
  const appointments = useQuery({
    queryKey: [
      "appointments",
      "calendar",
      business?.id,
      userId,
      detailRange.start,
      detailRange.end,
      businessTimeZone,
      serviceFilter,
      resourceFilter,
      statusFilter,
      branchFilter,
    ],
    queryFn: () =>
      appointmentsApi.listAll({
        business: business!.id,
        start_from: detailRange.start,
        start_to: detailRange.end,
        service: serviceFilter ? Number(serviceFilter) : "",
        resource: resourceFilter ? Number(resourceFilter) : "",
        status: statusFilter as Appointment["status"] | "",
        branch: branchFilter ? Number(branchFilter) : "",
      }),
    enabled: Boolean(business?.id) && detailsEnabled,
  });
  const yearSummary = useQuery({
    queryKey: ["appointments", "calendar-summary", business?.id, userId, businessTimeZone,
      calendarRange.start, calendarRange.end, serviceFilter, resourceFilter, statusFilter, branchFilter],
    queryFn: () => appointmentsApi.calendarSummary({
      business: business!.id, start_from: calendarRange.start, start_to: calendarRange.end,
      service: serviceFilter ? Number(serviceFilter) : "", resource: resourceFilter ? Number(resourceFilter) : "",
      status: statusFilter as Appointment["status"] | "", branch: branchFilter ? Number(branchFilter) : "",
    }),
    enabled: !!business?.id && viewMode === "year",
  });
  const outsideDay = inspectorOpen && viewMode !== "year" && (date < calendarRange.start || date >= calendarRange.end);
  const inspectorAppointments = useQuery({
    queryKey: ["appointments", "inspector-day", business?.id, userId, date, businessTimeZone, serviceFilter, resourceFilter, statusFilter, branchFilter],
    enabled: !!business?.id && outsideDay,
    queryFn: () => appointmentsApi.listAll({ business: business!.id, start_from: date, start_to: shiftDateValue(date, 1),
      service: serviceFilter, resource: resourceFilter, status: statusFilter, branch: branchFilter }),
  });
  const inspectorTasks = useQuery({
    queryKey: ["tasks", "inspector-day", business?.id, userId, date, businessTimeZone],
    enabled: !!business?.id && outsideDay && canViewTasks,
    queryFn: () => tasksApi.listAll({ business: business!.id, status: "active",
      due_from: taskDateISO(`${date}T00:00`, businessTimeZone),
      due_to: new Date(Date.parse(taskDateISO(`${shiftDateValue(date, 1)}T00:00`, businessTimeZone)!) - 1).toISOString() }),
  });
  const deepLinkedAppointment = useQuery({
    queryKey: [
      "appointments",
      "detail",
      business?.id,
      userId,
      appointmentIdFromUrl,
    ],
    queryFn: () => appointmentsApi.get(appointmentIdFromUrl!),
    enabled: Boolean(business?.id && appointmentIdFromUrl),
  });
  const dayAvailableSlots = useQuery({
    queryKey: [
      "available-slots",
      "calendar-day",
      scheduleBranch,
      business?.id,
      serviceFilter,
      resourceFilter,
      date,
    ],
    queryFn: () =>
      appointmentsApi.availableSlots({
        business_id: business!.id,
        service_id: Number(serviceFilter),
        branch_id: scheduleBranch ? Number(scheduleBranch) : "",
        resource_id: resourceFilter ? Number(resourceFilter) : "",
        date,
      }),
    enabled: Boolean(
      !branchesQuery.isLoading &&
      (!hasBranches || scheduleBranch) &&
      business?.id &&
      serviceFilter &&
      resourceFilter &&
      date,
    ),
  });
  const dateExceptions = useQuery({
    queryKey: ["schedule-exceptions", business?.id, resourceFilter, date],
    queryFn: () =>
      scheduleExceptionsApi.list({
        business: business!.id,
        resource: resourceFilter,
        date,
      }),
    enabled: Boolean(!hasBranches && business?.id && resourceFilter && date),
  });
  return {
    branchesQuery,
    hasBranches,
    scheduleBranch,
    branchCatalog,
    tasks,
    appointments,
    yearSummary,
    outsideDay,
    inspectorAppointments,
    inspectorTasks,
    deepLinkedAppointment,
    dayAvailableSlots,
    dateExceptions,
  };
}

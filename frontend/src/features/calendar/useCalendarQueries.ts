import { useQuery } from "@tanstack/react-query";
import { appointmentsApi } from "../../api/appointments";

import { branchesApi } from "../../api/branches";

import { scheduleExceptionsApi } from "../../api/workingHours";

import { useActiveBusiness } from "../../hooks/useBusiness";

import { tasksApi } from "../../api/tasks";
import { taskDateISO } from "../tasks/workspaceUtils";

import type { Appointment } from "../../types";

import { getCalendarRange } from "./calendarUtils";

type Args = {
  business: ReturnType<typeof useActiveBusiness>["business"];
  userId: number | undefined;
  canViewTasks: boolean;
  calendarRange: ReturnType<typeof getCalendarRange>;
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
  businessTimeZone,
  branchFilter,
  serviceFilter,
  resourceFilter,
  statusFilter,
  date,
  appointmentIdFromUrl,
}: Args) {
  const branchesQuery = useQuery({
    queryKey: ["branches", business?.id],
    queryFn: () => branchesApi.listAll({ business: business!.id }),
    enabled: !!business,
  });
  const hasBranches = !!branchesQuery.data?.length;
  const branchCatalog = useQuery({
    queryKey: ["branch-catalog", Number(branchFilter)],
    queryFn: () => branchesApi.catalog(Number(branchFilter)),
    enabled: !!branchFilter,
  });
  const tasks = useQuery({
    queryKey: [
      "tasks",
      "calendar",
      business?.id,
      userId,
      calendarRange.start,
      calendarRange.end,
      businessTimeZone,
    ],
    queryFn: () =>
      tasksApi.listAll({
        business: business!.id,
        status: "active",
        due_from: taskDateISO(`${calendarRange.start}T00:00`, businessTimeZone),
        due_to: new Date(
          Date.parse(
            taskDateISO(`${calendarRange.end}T00:00`, businessTimeZone)!,
          ) - 1,
        ).toISOString(),
      }),
    enabled: !!business?.id && canViewTasks,
  });
  const appointments = useQuery({
    queryKey: [
      "appointments",
      "calendar",
      business?.id,
      userId,
      calendarRange.start,
      calendarRange.end,
      serviceFilter,
      resourceFilter,
      statusFilter,
      branchFilter,
    ],
    queryFn: () =>
      appointmentsApi.listAll({
        business: business!.id,
        start_from: calendarRange.start,
        start_to: calendarRange.end,
        service: serviceFilter ? Number(serviceFilter) : "",
        resource: resourceFilter ? Number(resourceFilter) : "",
        status: statusFilter as Appointment["status"] | "",
        branch: branchFilter ? Number(branchFilter) : "",
      }),
    enabled: Boolean(business?.id),
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
      branchFilter,
      business?.id,
      serviceFilter,
      resourceFilter,
      date,
    ],
    queryFn: () =>
      appointmentsApi.availableSlots({
        business_id: business!.id,
        service_id: Number(serviceFilter),
        branch_id: branchFilter ? Number(branchFilter) : "",
        resource_id: resourceFilter ? Number(resourceFilter) : "",
        date,
      }),
    enabled: Boolean(
      !branchesQuery.isLoading &&
      (!hasBranches || branchFilter) &&
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
    branchCatalog,
    tasks,
    appointments,
    deepLinkedAppointment,
    dayAvailableSlots,
    dateExceptions,
  };
}

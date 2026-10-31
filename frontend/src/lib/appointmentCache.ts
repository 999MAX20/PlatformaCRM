import type { QueryClient } from "@tanstack/react-query";
import type { Appointment } from "../types";

export async function refreshAppointmentQueries(queryClient: QueryClient, appointment?: Appointment) {
  if (appointment) queryClient.setQueryData(["appointments", appointment.id], appointment);
  await Promise.all(["appointments", "available-slots", "crm-card", "activity-events", "tasks", "inbox-context"]
    .map(key => queryClient.invalidateQueries({ queryKey: [key] })));
}

import type { Appointment, CurrentUser, Id, Resource } from "../../types";
import { getPermissionScope } from "../../lib/permissions";
import type { Branch } from "../../api/branches";

export function canAccessAppointmentAction({
  appointment,
  resources,
  user,
  businessId,
  action = "update",
  branches,
}: {
  appointment: Appointment;
  resources: Resource[];
  user: CurrentUser | null;
  businessId: Id | undefined;
  action?: "update" | "delete";
  branches?: Branch[];
}) {
  if (appointment.branch && !branches?.some((branch) => branch.id === appointment.branch && branch.can_work)) return false;
  const scope = getPermissionScope(
    user,
    businessId,
    "appointments",
    action,
  );
  if (scope === "business") return true;
  if (scope !== "own" || !user?.id || !appointment.resource) return false;

  const resource = resources.find(
    (item) => Number(item.id) === Number(appointment.resource),
  );
  return Number(resource?.linked_user) === Number(user.id);
}

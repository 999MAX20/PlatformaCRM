import { hasPermission } from "./permissions";
import type { CurrentUser, Id, UserPreference } from "../types";

export const startPages: { value: UserPreference["start_page"]; label: string; resource?: string }[] = [
  { value: "dashboard", label: "nav.dashboard" },
  { value: "calendar", label: "nav.calendar", resource: "appointments" },
  { value: "tasks", label: "nav.tasks", resource: "tasks" },
  { value: "leads", label: "nav.leads", resource: "leads" },
  { value: "conversations", label: "nav.conversations", resource: "conversations" },
];

export function availableStartPages(user: CurrentUser | null, businessId?: Id) {
  return startPages.filter(({ resource }) => !resource || hasPermission(user, businessId, resource));
}

export function getUserStartPath(user: CurrentUser | null, businessId?: Id) {
  const selected = availableStartPages(user, businessId).find(({ value }) => value === user?.preferences?.start_page);
  return `/app/${selected?.value || "dashboard"}`;
}

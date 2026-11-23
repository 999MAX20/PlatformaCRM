import { apiClient } from "./client";
import type { Id } from "../types";

export type GoogleCalendar = { id: string; name: string; timezone: string };
export type GoogleCalendarBinding = {
  id: string; resource_id: number; resource_name: string; calendar_name: string;
  enabled: boolean; last_sync_at: string | null; error_code: string; stale: boolean; pending: boolean;
  coverage_start: string | null; coverage_end: string | null; next_sync_at: string | null;
};
type BindingList = { enabled: boolean; bindings: GoogleCalendarBinding[]; specialists: { id: number; name: string }[] };
const path = (id: Id, operation: string) => `/api/integrations/google/connections/${id}/calendar/${operation}/`;

export const googleCalendarApi = {
  bindings: async (id: Id) => (await apiClient.get<BindingList>(path(id, "bindings"))).data,
  calendars: async (id: Id) => (await apiClient.get<GoogleCalendar[]>(path(id, "calendars"))).data,
  bind: async (id: Id, resource_id: number, calendar_id: string) => (await apiClient.post<GoogleCalendarBinding>(
    path(id, "bind"), { resource_id, calendar_id, confirm_data_export: true })).data,
  enabled: async (id: Id, binding_id: string, enabled: boolean) => (await apiClient.post<GoogleCalendarBinding>(
    path(id, "enabled"), { binding_id, enabled })).data,
  sync: async (id: Id, binding_id: string) => (await apiClient.post<{ queued: boolean }>(path(id, "sync"), { binding_id })).data,
};

import { apiClient } from "./client";
import { createCrudApi } from "./crud";
import type { Appointment, Id, Resource } from "../types";

export type Branch = { id: Id; business: Id; name: string; address: string; phone: string; is_active: boolean; archived_at: string | null; can_manage: boolean; can_book: boolean; can_work: boolean };
export type BranchOffer = { id: Id; branch: Id; service: Id; service_name: string; duration_minutes: number; price_from: string | null; is_active: boolean };
export type BranchAssignment = { id: Id; branch: Id; resource: Id; resource_name: string; service_ids: Id[]; is_active: boolean };
export type Interval = { start: string; end: string };
export type BranchDay = { id: Id; branch: Id; resource: Id | null; weekday: number | null; date: string | null; intervals: Interval[] };
export type BranchTravel = { id: Id; from_branch: Id; to_branch: Id; minutes: number };
export type BranchCatalog = { offers: BranchOffer[]; assignments: BranchAssignment[]; days?: BranchDay[]; absences?: { resource_id: Id; starts_on: string; ends_on: string }[] };
export type BranchConfiguration = BranchCatalog & { days: BranchDay[]; travel: BranchTravel[] };
export type Absence = { id: Id; branch: Id | null; starts_on: string; ends_on: string; reason: "unavailable" | "vacation" | "sick" };
export type RetirementPreview = { pending: Record<string, number>; appointments: Appointment[]; appointments_count: number; appointments_truncated: boolean };
export const branchesApi = {
  ...createCrudApi<Branch>("/api/branches/"),
  configuration: async (id: Id) => (await apiClient.get<BranchConfiguration>(`/api/branches/${id}/configuration/`)).data,
  catalog: async (id: Id) => (await apiClient.get<BranchCatalog>(`/api/branches/${id}/catalog/`)).data,
  offer: async (id: Id, payload: Pick<BranchOffer, "service" | "duration_minutes" | "price_from" | "is_active">) => (await apiClient.post(`/api/branches/${id}/offers/`, payload)).data,
  assignment: async (id: Id, payload: Pick<BranchAssignment, "resource" | "service_ids" | "is_active">) => (await apiClient.post(`/api/branches/${id}/assignments/`, payload)).data,
  day: async (id: Id, payload: { resource?: Id | null; weekday?: number; date?: string; intervals: Interval[]; remove?: boolean }) => (await apiClient.post(`/api/branches/${id}/schedule/`, payload)).data,
  travel: async (id: Id, payload: { other_branch: Id; minutes: number }) => (await apiClient.post(`/api/branches/${id}/travel/`, payload)).data,
  state: async (id: Id, state: "active" | "paused" | "archived") => (await apiClient.post<Branch>(`/api/branches/${id}/state/`, { state })).data,
  grant: async (payload: { member: Id; branch_ids: Id[]; all_branches: boolean }) => (await apiClient.post("/api/branches/member-access/", payload)).data,
};
export const specialistLifecycleApi = {
  absences: async (id: Id) => (await apiClient.get<Absence[]>(`/api/resources/${id}/absences/`)).data,
  addAbsence: async (id: Id, payload: Omit<Absence, "id">) => (await apiClient.post<Absence>(`/api/resources/${id}/absences/`, payload)).data,
  removeAbsence: async (id: Id, absence: Id) => (await apiClient.post(`/api/resources/${id}/remove-absence/`, { absence })).data,
  preview: async (id: Id) => (await apiClient.get<RetirementPreview>(`/api/resources/${id}/retirement-preview/`)).data,
  retire: async (id: Id, disable_access: boolean) => (await apiClient.post<Resource>(`/api/resources/${id}/retire/`, { disable_access })).data,
};

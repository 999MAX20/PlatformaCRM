import { apiClient } from "./client";
import type { Branch, BranchAssignment, BranchOffer } from "./branches";
import type { Id } from "../types";

export type ManagementKind = "services" | "staff" | "rooms" | "branches";
export type ManagementService = { id: Id; name: string; description: string; duration_minutes: number; price_from: string | null; is_active: boolean; is_archived: boolean; requires_room: boolean; can_manage: boolean };
export type ManagementResource = { id: Id; name: string; profession: string; public_description: string; contact_phone: string; resource_type: string; branch: Id | null; is_active: boolean; retired_at: string | null; archived_at: string | null; inherit_schedule: boolean; can_manage: boolean };
export type ManagementCatalog = { scheduled_pairs: { branch: Id; resource: Id | null }[]; branches: Branch[]; services: ManagementService[]; resources: ManagementResource[]; offers: BranchOffer[]; assignments: BranchAssignment[]; room_options: { branch_id: Id; service_id: Id; resource_id: Id; is_alternative: boolean }[]; can_create_service: boolean; can_create_resource: boolean; can_delete: boolean; timezone: string };
type BaseInput = { business: Id; id?: Id; name: string; is_active?: boolean };
export type ServiceFormInput = BaseInput & { description: string; duration_minutes: number; price_from: string | null; requires_room: boolean; locations: { branch: Id; specialist_ids: Id[]; room_ids: Id[] }[] };
export type SpecialistFormInput = BaseInput & { profession: string; public_description: string; locations: { branch: Id; service_ids: Id[] }[] };
export type RoomFormInput = BaseInput & { public_description: string; branch: Id; service_ids: Id[]; inherit_schedule: boolean };
export type BranchFormInput = BaseInput & { city: string; address: string; phone: string; service_ids: Id[]; specialist_ids: Id[] };
export type LifecycleOperation = "activate" | "deactivate" | "archive" | "restore" | "delete";
export const managementApi = {
  catalog: async (business: Id) => (await apiClient.get<ManagementCatalog>("/api/management/", { params: { business } })).data,
  service: async (payload: ServiceFormInput) => (await apiClient.post<{ id: Id }>("/api/management/services/", payload)).data,
  specialist: async (payload: SpecialistFormInput) => (await apiClient.post<{ id: Id }>("/api/management/staff/", payload)).data,
  room: async (payload: RoomFormInput) => (await apiClient.post<{ id: Id }>("/api/management/rooms/", payload)).data,
  branch: async (payload: BranchFormInput) => (await apiClient.post<{ id: Id }>("/api/management/branches/", payload)).data,
  lifecycle: async (payload: { business: Id; id: Id; kind: ManagementKind; operation: LifecycleOperation }) => (await apiClient.post("/api/management/lifecycle/", payload)).data,
};

import { apiClient } from "./client";

export type MedicalRoleKind = "doctor" | "assistant" | "reception" | "head";
export type MedicalRolePermission = { resource: string; action: string; scope: "own" | "team" | "business" };
export type MedicalRoleDefinition = { id: number; name: string; kind: MedicalRoleKind; is_active: boolean;
  permissions: Array<MedicalRolePermission & { is_allowed: boolean }> };
export type MedicalRoleMember = { id: number; name: string; is_active: boolean; account_active: boolean };
export type MedicalRolePage<T> = { results: T[]; next_after_id: number | null };
export type MedicalRolePageScope = { business_id: number; after_id?: number; limit?: number; query?: string };
export type MedicalRoleAssignment = { member: number; role: number; kind: MedicalRoleKind; all_branches: boolean;
  branches: number[]; revision: number; granted_by: number; granted_at: string; revoked_at: string | null };
export type MedicalRoleContext = { member: MedicalRoleMember; assignment: MedicalRoleAssignment | null;
  assigned_branches: Array<{ id: number; name: string; is_active: boolean }>;
  role_name: string | null; role_active: boolean | null; can_assign: boolean; can_revoke: boolean; can_assign_all_branches: boolean };
export type MedicalRoleAccess = { can_assign: boolean;
  permissions_by_kind: Record<MedicalRoleKind, Array<{ resource: string; actions: string[] }>> };
export type MedicalRoleDecision = { id: number; revision: number; action: "grant" | "revoke";
  actor_name: string; created_at: string; reason: string };
export type MedicalRoleResult = { id: number; revision: number; revoked_at: string | null; replayed: boolean };
export type MedicalRoleCreate = { business_id: number; name: string; kind: MedicalRoleKind; permissions: MedicalRolePermission[] };
export type MedicalRoleRevoke = { business_id: number; member_id: number; expected_revision: number; reason: string };
export type MedicalRoleAssign = MedicalRoleRevoke & { role_id: number; all_branches: boolean; branch_ids: number[] };
const root = "/api/medical/role-management/";
async function read<T>(path: string, params: object, signal?: AbortSignal) {
  return (await apiClient.get<T>(root + path + "/", { params, signal })).data;
}
async function command<T>(path: string, payload: object, key: string, signal?: AbortSignal) {
  if (!key.trim() || key.length > 128) throw new Error("Medical command requires an idempotency key of at most 128 characters.");
  return (await apiClient.post<T>(root + path + "/", payload, { headers: { "Idempotency-Key": key }, signal })).data;
}
export const medicalRolesApi = {
  access: (business_id: number, signal?: AbortSignal) => read<MedicalRoleAccess>("workspace", { business_id }, signal),
  roles: (scope: MedicalRolePageScope, signal?: AbortSignal) => read<MedicalRolePage<MedicalRoleDefinition>>("roles", scope, signal),
  members: (scope: MedicalRolePageScope, signal?: AbortSignal) => read<MedicalRolePage<MedicalRoleMember>>("members", scope, signal),
  context: (scope: { business_id: number; member_id: number }, signal?: AbortSignal) => read<MedicalRoleContext>("member-context", scope, signal),
  branches: (scope: MedicalRolePageScope & { member_id: number }, signal?: AbortSignal) => read<MedicalRolePage<{ id: number; name: string }>>("branches", scope, signal),
  history: (scope: Omit<MedicalRolePageScope, "query"> & { member_id: number }, signal?: AbortSignal) => read<MedicalRolePage<MedicalRoleDecision>>("history", scope, signal),
  create: (payload: MedicalRoleCreate, key: string, signal?: AbortSignal) => command<{ id: number; replayed: boolean }>("roles", payload, key, signal),
  assign: (payload: MedicalRoleAssign, key: string, signal?: AbortSignal) => command<MedicalRoleResult>("assign", payload, key, signal),
  revoke: (payload: MedicalRoleRevoke, key: string, signal?: AbortSignal) => command<MedicalRoleResult>("revoke", payload, key, signal),
};

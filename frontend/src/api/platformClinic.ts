import { apiClient } from "./client";
import type { PlatformPage } from "./platform";

export const clinicKinds = ["clients", "leads", "deals", "tasks", "appointments", "conversations", "payments", "connectors", "channels"] as const;
export type ClinicKind = typeof clinicKinds[number];
export type ClinicValue = string | number | boolean | string[] | null;
export type ClinicRecord = {
  id: number; kind: ClinicKind; business_id: number; title: string; status: string | null; is_archived: boolean;
  created_at: string; updated_at: string; fields: Record<string, ClinicValue>;
  relations: { field: string; kind: ClinicKind | null; id: number; label: string }[];
  people: { field: string; id: number; name: string; active: boolean }[];
  sections?: string[]; business?: { id: number; name: string; timezone: string };
};
export type ClinicChild = { id: number; created_at: string; text?: string; label?: string; value?: ClinicValue; author?: string | null; direction?: string; sender_type?: string; status?: string; event_type?: string };
export type ClinicAccess = { id: number; created_at: string; actor: string | null; resource: string; record_id: number | null };
const root = (business: string) => `/api/platform/merchants/${business}`;
export const platformClinicApi = {
  list: async (business: string, kind: ClinicKind, params: Record<string, string | number>) => (await apiClient.get<PlatformPage<ClinicRecord>>(`${root(business)}/crm/${kind}/`, { params })).data,
  detail: async (business: string, kind: ClinicKind, id: number) => (await apiClient.get<ClinicRecord>(`${root(business)}/crm/${kind}/${id}/`)).data,
  children: async (business: string, kind: ClinicKind, id: number, section: string, page: number) => (await apiClient.get<PlatformPage<ClinicChild>>(`${root(business)}/crm/${kind}/${id}/${section}/`, { params: { page, page_size: 20 } })).data,
  access: async (business: string, page: number) => (await apiClient.get<PlatformPage<ClinicAccess>>(`${root(business)}/crm-access-log/`, { params: { page, page_size: 20 } })).data,
};

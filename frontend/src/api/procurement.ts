import { apiClient } from "./client";
export type PurchaseScope = { business_id: number; branch_id: number };
export type PurchaseFields = { material: string; specification: string; quantity: string; unit: string; urgent: boolean; needed_by: string | null; comment: string };
export type PurchaseRequest = PurchaseFields & { id: number; branch_id: number; author_name: string; created_at: string; state: string; revision: number; received: string };
export type PurchaseHistory = { id: number; actor_name: string; created_at: string; action: string; reason: string; snapshot: PurchaseRequest };
export type PurchaseContext = { branches: { id: number; name: string }[] };
const root = "/api/procurement/requests/";
export const procurementApi = {
  context: async (business_id: number, signal?: AbortSignal) => (await apiClient.get<PurchaseContext>(root+"context/", { params: { business_id }, signal })).data,
  list: async (scope: PurchaseScope, after_id = 0, signal?: AbortSignal) => (await apiClient.get<{ results: PurchaseRequest[]; next_id: number | null }>(root, { params: {...scope, after_id}, signal })).data,
  create: async (scope: PurchaseScope, fields: PurchaseFields, key: string) => (await apiClient.post<PurchaseRequest>(root, {...scope, fields}, {headers:{"Idempotency-Key":key}})).data,
  change: async (scope: PurchaseScope, item: PurchaseRequest, action: string, reason: string, fields: PurchaseFields | undefined, key: string) =>
    (await apiClient.post<PurchaseRequest>(`${root}${item.id}/change/`, {...scope, expected_revision:item.revision, action, reason, ...(fields ? {fields}: {})}, {headers:{"Idempotency-Key":key}})).data,
  history: async (scope: PurchaseScope, id: number, after_id=0, signal?: AbortSignal) => (await apiClient.get<{results:PurchaseHistory[];next_id:number|null}>(`${root}${id}/history/`,{params:{...scope,after_id},signal})).data,
};

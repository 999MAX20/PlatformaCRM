import { apiClient } from "./client";
import type { AIToolCallLog, FinancialReport, Id } from "../types";

export type CRMEntity = "clients" | "leads" | "deals" | "tasks" | "appointments";
export type CRMRecord = { id: Id; full_name?: string; title?: string; message?: string; start_at?: string; status?: string; is_archived?: boolean } & Record<string, unknown>;
export type CRMReadResult = { entity: CRMEntity; count: number; offset: number; limit: number; has_more: boolean; results: CRMRecord[] };
export type HistoryReport = {
  period: { start: string; end: string }; previous_period: { start: string; end: string }; timezone: string;
  financial: FinancialReport; previous_financial: FinancialReport;
  financial_change: Record<"receipts" | "refunds" | "net_receipts", { absolute: string | null; percent: string | null }>;
  operations: Partial<Record<CRMEntity, { count: number; previous_count: number; difference: number; current_statuses: Record<string, number> }>>;
  series: { granularity: "day" | "month" | null; points: Array<{ period: string; receipts: string; refunds: string; net_receipts: string; count: number }> };
  state: "available" | "no_data";
};
export const aiCRMApi = {
  read: async (params: { business: Id; entity: CRMEntity; query?: string; offset?: number; include_archived?: boolean }) =>
    (await apiClient.get<CRMReadResult>("/api/ai/crm/read/", { params })).data,
  plan: async (payload: { business: Id; entity: CRMEntity; entity_id?: Id; message: string }) =>
    (await apiClient.post<{ question: string; suggested_actions: AIToolCallLog[] }>("/api/ai/crm/plan/", payload)).data,
  history: async (params: { business: Id; start: string; end: string }) =>
    (await apiClient.get<HistoryReport>("/api/ai/analyst/history/", { params })).data,
  explainHistory: async (payload: { business: Id; start: string; end: string; question: string }) =>
    (await apiClient.post<{ answer: string; sources: Array<{ id: string; label: string }>; provider_state: string; report: HistoryReport }>("/api/ai/analyst/history/", payload)).data,
};

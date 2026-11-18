import { apiClient, unwrapList } from "./client";
import { createCrudApi } from "./crud";
import type { AuditLog, Id, LoginHistory, SecurityRiskSummary, SupportAccessGrant } from "../types";

type HistoryParams = { business?: Id; page: number; date_from?: string; status?: string };
type HistoryPage<T> = { count: number; next: string | null; previous: string | null; results: T[] };

export const securityApi = {
  auditPage: async (params: HistoryParams) => {
    const { data } = await apiClient.get<HistoryPage<AuditLog>>("/api/security/audit/", { params: { ...params, paginate: "true" } });
    return data;
  },
  loginHistoryPage: async (params: HistoryParams) => {
    const { data } = await apiClient.get<HistoryPage<LoginHistory>>("/api/security/login-history/", { params: { ...params, paginate: "true" } });
    return data;
  },
  audit: async (params: { business?: Id; actor?: Id | string; entity_type?: string; action?: string; risk?: string; category?: string }) => {
    const { data } = await apiClient.get<AuditLog[] | { results: AuditLog[] }>("/api/security/audit/", { params });
    return unwrapList(data);
  },
  loginHistory: async (params: { business?: Id; status?: string }) => {
    const { data } = await apiClient.get<LoginHistory[] | { results: LoginHistory[] }>("/api/security/login-history/", { params });
    return unwrapList(data);
  },
  riskSummary: async (business?: Id) => {
    const { data } = await apiClient.get<SecurityRiskSummary>("/api/security/risk-summary/", { params: { business } });
    return data;
  },
  supportGrants: createCrudApi<SupportAccessGrant>("/api/security/support-grants/"),
};

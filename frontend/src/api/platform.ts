import { apiClient } from "./client";
import type { PlatformMerchant, PlatformOperationsHealth, PlatformOverview, PlatformSupportAction } from "../types";
import type { OperationFilters, OperationPage } from "../types/platformOperations";

export type PlatformPage<T> = { count: number; next: string | null; previous: string | null; results: T[] };

export const platformApi = {
  operationsWorklist: async (params: OperationFilters) => (await apiClient.get<OperationPage>("/api/platform/operations-worklist/", { params })).data,
  overview: async () => {
    const { data } = await apiClient.get<PlatformOverview>("/api/platform/overview/");
    return data;
  },
  operationsHealth: async () => {
    const { data } = await apiClient.get<PlatformOperationsHealth>("/api/platform/operations-health/");
    return data;
  },
  merchants: async (params: { search?: string; page?: number; page_size?: number; status?: string; service?: string } = {}) => {
    const { data } = await apiClient.get<PlatformPage<PlatformMerchant>>("/api/platform/merchants/", { params });
    return data;
  },
  supportActions: async (id: string, page = 1) => {
    const { data } = await apiClient.get<PlatformPage<PlatformSupportAction>>(`/api/platform/merchants/${id}/support-actions/`, { params: { page, page_size: 10 } });
    return data;
  },
  merchant: async (id: number | string) => {
    const { data } = await apiClient.get<PlatformMerchant>(`/api/platform/merchants/${id}/`);
    return data;
  },
  createSupportAction: async (id: number | string, payload: { action_type?: string; note: string; status?: string }, stepUpToken: string) => {
    const { data } = await apiClient.post<PlatformSupportAction>(
      `/api/platform/merchants/${id}/support-actions/`,
      payload,
      { headers: { "X-Zani-MFA-Step-Up": stepUpToken } },
    );
    return data;
  },
};

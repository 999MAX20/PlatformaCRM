import { apiClient, type PaginatedResponse } from "./client";
import { createCrudApi } from "./crud";
import type { Id, Service } from "../types";

export type ServiceListParams = {
  business?: Id;
  search?: string;
  status?: "active" | "inactive" | "archived" | "";
  page?: number;
  page_size?: number;
};

export type ServiceSummary = {
  active: number;
  average_duration_minutes: number | null;
  used_in_bookings: number;
};

export type ServicePage = PaginatedResponse<Service> & { summary?: ServiceSummary };

const serviceCrudApi = createCrudApi<Service>("/api/services/");

export const servicesApi = {
  ...serviceCrudApi,
  listPage: async (params?: ServiceListParams): Promise<ServicePage> => {
    const requestParams = params?.status === "archived"
      ? { ...params, include_archived: true }
      : params;
    const { data } = await apiClient.get<Service[] | ServicePage>("/api/services/", { params: requestParams });
    if (Array.isArray(data)) {
      return {
        count: data.length,
        next: null,
        previous: null,
        results: data,
      } satisfies PaginatedResponse<Service>;
    }
    return data;
  },
  activate: async (id: Id) => {
    const { data } = await apiClient.post<Service>(`/api/services/${id}/activate/`);
    return data;
  },
  deactivate: async (id: Id) => {
    const { data } = await apiClient.post<Service>(`/api/services/${id}/deactivate/`);
    return data;
  },
};

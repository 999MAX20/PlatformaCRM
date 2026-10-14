import { apiClient } from "./client";

export type ServiceState = "healthy" | "degraded" | "unknown";
export type ServiceStatus = {
  status: ServiceState;
  checked_at: string;
  max_age_seconds: number;
  components: Array<{
    component: "automations" | "notifications" | "exports" | "files";
    state: ServiceState;
    last_state: Exclude<ServiceState, "unknown"> | null;
    observed_at: string | null;
    started_at: string | null;
    recovered_at: string | null;
    episode: number;
  }>;
};

export async function getServiceStatus(businessId: string | number, signal?: AbortSignal) {
  const { data } = await apiClient.get<ServiceStatus>("/api/service-status/", { params: { business: businessId }, signal });
  return data;
}

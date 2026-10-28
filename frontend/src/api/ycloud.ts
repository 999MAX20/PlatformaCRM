import { apiClient } from "./client";
import type { Id } from "../types";

export type YCloudStatus = {
  available: boolean;
  status: "not_connected" | "pending" | "connected" | "expired" | "cancelled";
  channel_status: string;
  phone_number: string;
  expires_at: string | null;
  error_code: string;
  failed_events: number;
};

export const ycloudApi = {
  status: async (channelId: Id) => (await apiClient.get<YCloudStatus>(`/api/integrations/ycloud/channels/${channelId}/`)).data,
  start: async (channelId: Id) => (await apiClient.post<{ onboarding_url: string; expires_at: string }>(`/api/integrations/ycloud/channels/${channelId}/`, { action: "start" })).data,
  recover: async (channelId: Id, action: "cancel" | "retry_events") => {
    await apiClient.post(`/api/integrations/ycloud/channels/${channelId}/`, { action });
  },
};

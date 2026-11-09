import { apiClient } from "./client";
import type { Id } from "../types";

export type YCloudOnboardingType = "WHATSAPP_BUSINESS_PLATFORM" | "WHATSAPP_BUSINESS_APP";

export type YCloudStatus = {
  available: boolean;
  status: "not_connected" | "pending" | "connected" | "expired" | "cancelled";
  channel_status: string;
  phone_number: string;
  expires_at: string | null;
  error_code: string;
  failed_events: number;
  onboarding_type: YCloudOnboardingType;
  expected_phone_number: string;
};

export const ycloudApi = {
  status: async (channelId: Id) => (await apiClient.get<YCloudStatus>(`/api/integrations/ycloud/channels/${channelId}/`)).data,
  start: async (channelId: Id, onboardingType: YCloudOnboardingType = "WHATSAPP_BUSINESS_PLATFORM", expectedPhoneNumber = "") =>
    (await apiClient.post<{ onboarding_url: string; expires_at: string }>(`/api/integrations/ycloud/channels/${channelId}/`, {
      action: "start", onboarding_type: onboardingType, expected_phone_number: expectedPhoneNumber,
    })).data,
  recover: async (channelId: Id, action: "cancel" | "retry_events") => {
    await apiClient.post(`/api/integrations/ycloud/channels/${channelId}/`, { action });
  },
};

import { apiClient } from "./client";
import type { PaginatedResponse } from "./client";
import { createCrudApi } from "./crud";
import type { Id, Notification, NotificationPreference } from "../types";

export type NotificationSummary = {
  pending: number;
  failed: number;
  due: number;
  unread: number;
  urgent: number;
  by_category: Record<string, number>;
  can_manage_announcements?: boolean;
};

export type Announcement = {
  id: Id;
  business: Id;
  text: string;
  priority: Notification["priority"];
  author_name: string;
  created_at: string;
  revoked_at: string | null;
  recipient_count: number;
  opened_count: number;
  read_count: number;
  acknowledged_count: number;
};

export type AnnouncementRecipient = {
  id: Id;
  user: Id;
  name: string;
  received_at: string;
  opened_at: string | null;
  read_at: string | null;
  acknowledged_at: string | null;
};

export const notificationsApi = {
  ...createCrudApi<Notification>("/api/notifications/"),
  preferences: {
    ...createCrudApi<NotificationPreference>("/api/notification-preferences/"),
    list: async (params?: { user?: Id | "me"; category?: Notification["category"] }) => {
      const { data } = await apiClient.get<NotificationPreference[] | { results: NotificationPreference[] }>("/api/notification-preferences/", { params });
      return Array.isArray(data) ? data : data.results;
    },
  },
  summary: async (params?: { surface?: "bell"; business?: Id }) => {
    const { data } = await apiClient.get<NotificationSummary>("/api/notifications/summary/", { params });
    return data;
  },
  markSent: async (id: Id) => {
    const { data } = await apiClient.post<Notification>(`/api/notifications/${id}/mark-sent/`);
    return data;
  },
  markRead: async (id: Id, business?: Id) => {
    const { data } = await apiClient.post<Notification>(`/api/notifications/${id}/mark-read/`, {}, { params: { business } });
    return data;
  },
  markUnread: async (id: Id, business?: Id) => {
    const { data } = await apiClient.post<Notification>(`/api/notifications/${id}/mark-unread/`, {}, { params: { business } });
    return data;
  },
  markAllRead: async (params?: { surface?: "bell"; business?: Id }) => {
    const { data } = await apiClient.post<{ updated: number }>("/api/notifications/mark-all-read/", {}, { params });
    return data;
  },
  personalPage: async (business: Id, page = 1) => {
    const { data } = await apiClient.get<PaginatedResponse<Notification>>("/api/notifications/", { params: { business, surface: "bell", page } });
    return data;
  },
  personalDetail: async (id: Id, business: Id) => {
    const { data } = await apiClient.get<Notification>(`/api/notifications/${id}/`, { params: { business } });
    return data;
  },
  open: async (id: Id, business: Id) => {
    const { data } = await apiClient.post<Notification>(`/api/notifications/${id}/open/`, {}, { params: { business } });
    return data;
  },
  acknowledge: async (id: Id, business: Id) => {
    const { data } = await apiClient.post<Notification>(`/api/notifications/${id}/acknowledge/`, {}, { params: { business } });
    return data;
  },
  announcements: async (business: Id, page = 1) => {
    const { data } = await apiClient.get<PaginatedResponse<Announcement> & { events_enabled?: boolean }>("/api/notifications/announcements/", { params: { business, page } });
    return data;
  },
  publish: async (business: Id, payload: { text: string; priority: Notification["priority"]; publication_key: string }) => {
    const { data } = await apiClient.post<Announcement>("/api/notifications/announcements/", payload, { params: { business } });
    return data;
  },
  recipients: async (id: Id, business: Id, page = 1) => {
    const { data } = await apiClient.get<PaginatedResponse<AnnouncementRecipient> & { announcement: Announcement }>(
      `/api/notifications/${id}/announcement-recipients/`, { params: { business, page } },
    );
    return data;
  },
  revoke: async (id: Id, business: Id) => {
    const { data } = await apiClient.post<Announcement>(`/api/notifications/${id}/revoke-announcement/`, {}, { params: { business } });
    return data;
  },
  cancel: async (id: Id) => {
    const { data } = await apiClient.post<Notification>(`/api/notifications/${id}/cancel/`);
    return data;
  },
  retry: async (id: Id, business?: Id) => {
    const { data } = await apiClient.post<{ result: Record<string, unknown>; notification: Notification }>(`/api/notifications/${id}/retry/`, {}, { params: { business } });
    return data;
  },
};

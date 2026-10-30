import type { Id } from "./core";

export type Service = {
  appointment_count?: number;
  id: Id;
  business: Id;
  name: string;
  description: string;
  duration_minutes: number;
  price_from: string | null;
  is_active: boolean;
  is_archived: boolean;
  archived_at: string | null;
  archived_by: Id | null;
  archive_reason: string;
  created_at: string;
  updated_at: string;
};

export type Resource = {
  profession?: string;
  public_description?: string;
  contact_phone?: string;
  retired_at?: string | null;
  id: Id;
  business: Id;
  name: string;
  resource_type: "staff" | "room" | "hall" | "box" | "equipment" | "other";
  linked_user: Id | null;
  linked_user_name?: string;
  linked_user_email?: string | null;
  is_active: boolean;
  appointment_count?: number;
  has_individual_schedule?: boolean;
  weekly_schedule?: Array<Pick<WorkingHours, "weekday" | "start_time" | "end_time" | "is_day_off">>;
  created_at: string;
  updated_at: string;
};

export type WorkingHours = {
  id: Id;
  business: Id;
  resource: Id | null;
  weekday: number;
  start_time: string;
  end_time: string;
  is_day_off: boolean;
};

export type ScheduleException = Omit<WorkingHours, "weekday" | "resource"> & {
  resource: Id;
  date: string;
};

export type AppointmentMessageSetting = {
  available_channels?: string[];
  id: Id;
  business: Id;
  scenario: "confirmation" | "reminder" | "thank_you";
  label: string;
  is_enabled: boolean;
  offset_minutes: number;
  channel_policy: "auto" | "telegram" | "whatsapp" | "email" | "sms" | "system";
  template_text: string;
  created_at: string;
  updated_at: string;
};

export type AvailableSlot = {
  start_at: string;
  end_at: string;
};

import type { Id } from "./core";

export type Business = {
  id: Id;
  owner: Id;
  name: string;
  slug: string;
  business_type: "dentistry" | "beauty" | "sauna" | "autoservice" | "education" | "medical" | "other";
  city: string;
  address: string;
  phone: string;
  whatsapp: string;
  telegram: string;
  instagram: string;
  timezone: string;
  language: "ru" | "kk" | "en" | string;
  currency: "KZT" | "USD" | "EUR" | "RUB" | string;
  financial_source_mode?: "external" | "manual";
  financial_connector?: Id | null;
  legal_name: string;
  tax_id: string;
  invoice_email: string;
  brand_color: string;
  brand_logo_url: string;
  cancellation_policy: string;
  prepayment_policy: string;
  sla_minutes: number;
  booking_buffer_minutes: number;
  landing_id?: string;
  landing_domain?: string;
  landing_preview_url?: string;
  status: "active" | "inactive" | "trial" | "blocked";
  created_at: string;
  updated_at: string;
};

export type OnboardingTemplate = {
  key: Business["business_type"];
  label: string;
  services: string[];
  resources: string[];
  stages: string[];
  quick_replies: string[];
};

export type OnboardingChecklistItem = {
  key: string;
  title: string;
  is_completed: boolean;
};

export type OnboardingStatus = {
  business: Id;
  progress: number;
  completed: number;
  total: number;
  items: OnboardingChecklistItem[];
};

export type ApplyOnboardingTemplateResponse = {
  business: Id;
  template_key: Business["business_type"];
  pipeline: Id;
  services_count: number;
  resources_count: number;
  quick_replies_count: number;
  automations_count: number;
  checklist: OnboardingStatus;
};

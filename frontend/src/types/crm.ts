import type { Id } from "./core";
import type { Task } from "./tasks";
import type { Lead, Deal, Appointment, DuplicateClient } from "./index";
import type { BotConversation } from "./conversations";
import type { ActivityEvent } from "./activity";
import type { FileAttachment } from "./files";

export type Client = {
  id: Id;
  business: Id;
  full_name: string;
  phone: string;
  email: string;
  whatsapp_id: string;
  telegram_id: string;
  instagram_id: string;
  source: "website" | "telegram" | "whatsapp" | "instagram" | "manual" | "parser" | "other";
  source_detail: string;
  source_context_json: Record<string, unknown>;
  notes: string;
  manager_user_id?: number | null;
  manager_name?: string | null;
  is_active?: boolean;
  has_no_reply?: boolean;
  is_vip?: boolean;
  leads_count?: number;
  deals_count?: number;
  appointments_count?: number;
  tasks_count?: number;
  conversations_count?: number;
  last_activity_at?: string | null;
  next_step_title?: string;
  next_step_kind?: "task" | "reply" | "appointment" | "contact";
  next_step_date?: string | null;
  next_step_priority?: Task["priority"] | "";
  is_archived?: boolean;
  archived_at?: string | null;
  archived_by?: Id | null;
  archive_reason?: string;
  created_at: string;
  updated_at: string;
};

export type LeadSummary = {
  total: number;
  new: number;
  new_this_week: number;
  unanswered: number;
  unanswered_this_week: number;
  in_progress: number;
  in_progress_this_week: number;
  hot: number;
  hot_this_week: number;
  attention: number;
  mine: number;
  by_status: Partial<Record<Lead["status"], number>>;
  by_source: Partial<Record<Lead["source"], number>>;
};

export type Pipeline = {
  id: Id;
  business: Id;
  name: string;
  slug: string;
  entity_type: "deal";
  is_default: boolean;
  template_key: string;
  stages?: PipelineStage[];
  created_at: string;
  updated_at: string;
};

export type PipelineStage = {
  id: Id;
  business: Id;
  pipeline: Id;
  name: string;
  template_key: string;
  is_active: boolean;
  order: number;
  color: string;
  probability: number;
  sla_minutes: number | null;
  required_fields_json?: { fields?: string[] } & Record<string, unknown>;
  allowed_roles_json?: { roles?: string[] } & Record<string, unknown>;
  is_won: boolean;
  is_lost: boolean;
  created_at: string;
  updated_at: string;
};

export type DealBoardStage = PipelineStage & {
  count: number;
  offset: number;
  limit: number;
  has_more: boolean;
  deals: Deal[];
};

export type DealBoard = {
  stages: DealBoardStage[];
};

export type Note = {
  id: Id;
  business: Id;
  client: Id | null;
  author: Id | null;
  entity_type: string;
  entity_id: string;
  text: string;
  created_at: string;
  updated_at: string;
};

export type CrmEntityType = "client" | "lead" | "deal" | "appointment";

export type CrmCardActionDetail = {
  id: string;
  label_key: string;
  resource: string;
  action: string;
  allowed: boolean;
  scope: "none" | "own" | "team" | "business" | string;
  reason: string;
  requires_reason: boolean;
  destructive: boolean;
  confirmation: "none" | "confirm" | "reason" | string;
};

export type Tag = {
  id: Id;
  business: Id;
  name: string;
  color: string;
  source: "manual" | "ai" | "behavior" | "automation";
  created_at: string;
  updated_at: string;
};

export type TaggedObject = {
  id: Id;
  business: Id;
  tag: Id;
  tag_name?: string;
  tag_color?: string;
  entity_type: CrmEntityType | string;
  entity_id: string;
  created_at: string;
};

export type SegmentFilter = {
  id: Id;
  business: Id;
  segment: Id;
  field: "full_name" | "phone" | "email" | "source" | "notes" | "tag" | "created_at";
  operator: "equals" | "contains" | "in" | "gte" | "lte" | "is_empty" | "not_empty";
  value_json: { value?: unknown; values?: unknown[] } & Record<string, unknown>;
  sort_order: number;
  created_at: string;
  updated_at: string;
};

export type Segment = {
  id: Id;
  business: Id;
  name: string;
  description: string;
  entity_type: "client";
  is_active: boolean;
  cached_count: number;
  last_evaluated_at: string | null;
  filters: SegmentFilter[];
  created_at: string;
  updated_at: string;
};

export type CrmCardPayload = {
  primary_entity?: {
    type: CrmEntityType;
    id: Id;
  } | null;
  available_actions?: string[];
  available_action_details?: CrmCardActionDetail[];
  meta?: {
    related_counts: {
      leads: number;
      deals: number;
      appointments: number;
      tasks: number;
      conversations: number;
      timeline: number;
      notes: number;
    };
    limits: {
      related: number;
      timeline: number;
      notes: number;
    };
    has_more: {
      leads: boolean;
      deals: boolean;
      appointments: boolean;
      tasks: boolean;
      conversations: boolean;
      timeline: boolean;
      notes: boolean;
    };
  };
  client: Client | null;
  lead: Lead | null;
  deal: Deal | null;
  appointment: Appointment | null;
  leads: Lead[];
  deals: Deal[];
  appointments: Appointment[];
  tasks: Task[];
  conversations: BotConversation[];
  timeline: ActivityEvent[];
  notes: Note[];
  tags: TaggedObject[];
  attachments: FileAttachment[];
  consents: Array<{
    channel: "telegram" | "whatsapp";
    status: "opted_in" | "opted_out" | "unknown";
    source: string;
    note: string;
    opted_in_at: string | null;
    opted_out_at: string | null;
  }>;
  custom_fields: CrmCardCustomField[];
};

export type DuplicateCheckResponse = {
  duplicates: DuplicateClient[];
};

export type CustomFieldDefinition = {
  id: Id;
  business: Id;
  entity_type: CrmEntityType;
  key: string;
  label: string;
  field_type:
    | "text"
    | "textarea"
    | "number"
    | "money"
    | "date"
    | "datetime"
    | "select"
    | "multiselect"
    | "boolean"
    | "phone"
    | "email"
    | "url";
  options_json: { options?: Array<string | { value?: string; key?: string; label?: string }> } & Record<string, unknown>;
  permissions_json: { view_roles?: string[]; edit_roles?: string[] } & Record<string, unknown>;
  is_required: boolean;
  is_active: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
};

export type CustomFieldValue = {
  id: Id;
  business: Id;
  definition: Id;
  entity_type: CrmEntityType;
  entity_id: string;
  value_json: { value?: unknown } & Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type CrmCardCustomField = {
  definition: CustomFieldDefinition;
  value: CustomFieldValue | null;
  can_edit?: boolean;
};

export type LeadFormField = {
  id: Id;
  form: Id;
  label: string;
  key: string;
  field_type: "text" | "textarea" | "phone" | "email" | "select";
  placeholder: string;
  options_json: Record<string, unknown>;
  is_required: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
};

export type LeadCaptureForm = {
  id: Id;
  business: Id;
  name: string;
  public_id: string;
  landing_id?: string;
  landing_domain?: string;
  preview_url?: string;
  title: string;
  description: string;
  source: Lead["source"];
  success_message: string;
  default_responsible_user: Id | null;
  is_active: boolean;
  fields: LeadFormField[];
  submissions_count?: number;
  created_at: string;
  updated_at: string;
};

export type LeadFormSubmission = {
  id: Id;
  form: Id;
  form_name?: string;
  business: Id;
  client: Id | null;
  lead: Id | null;
  payload_json: Record<string, unknown>;
  utm_json: Record<string, unknown>;
  source_context_json?: Record<string, unknown>;
  duplicate_json: Record<string, unknown>;
  landing_id?: string;
  page_url?: string;
  page_domain?: string;
  ip_address?: string | null;
  user_agent: string;
  created_at: string;
};

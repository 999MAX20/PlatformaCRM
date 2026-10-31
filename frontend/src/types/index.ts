// Compatibility entry point. In-progress contract edits stay here until their own delivery.
import type { Id } from "./core";
import type { Client, DuplicateCheckResponse } from "./crm";
import type { Task } from "./tasks";

export type Lead = {
  attention_reasons?: Array<"unassigned" | "no_action" | "overdue_action">;
  id: Id;
  business: Id;
  client: Id;
  client_name?: string;
  client_phone?: string;
  client_email?: string;
  service: Id | null;
  service_name?: string;
  source: Client["source"] | "landing";
  message: string;
  status: "new" | "in_progress" | "appointment_created" | "contacted" | "closed" | "lost";
  previous_status?: string;
  lost_reason?: string;
  lost_at?: string | null;
  lost_by?: Id | null;
  responsible_user: Id | null;
  next_task_id?: Id | null;
  next_task_title?: string | null;
  next_task_due_at?: string | null;
  responsible_name?: string;
  responsible_email?: string;
  ai_score?: number;
  loss_risk?: number;
  recommended_action?: string;
  is_archived?: boolean;
  archived_at?: string | null;
  archived_by?: Id | null;
  archive_reason?: string;
  created_at: string;
  updated_at: string;
};

export type Deal = {
  id: Id;
  business: Id;
  client: Id;
  client_name?: string;
  client_phone?: string;
  client_email?: string;
  lead: Id | null;
  pipeline: Id;
  stage: Id;
  stage_name?: string;
  stage_template_key?: string;
  stage_color?: string;
  stage_order?: number;
  stage_probability?: number;
  stage_is_won?: boolean;
  stage_is_lost?: boolean;
  title: string;
  amount: string;
  currency: string;
  probability: number;
  expected_close_at: string | null;
  owner: Id | null;
  owner_name?: string;
  owner_email?: string;
  status: "open" | "won" | "lost";
  source: string;
  lost_reason?: string;
  lost_by?: Id | null;
  previous_status?: string;
  previous_stage?: Id | null;
  won_at?: string | null;
  lost_at?: string | null;
  is_archived?: boolean;
  archived_at?: string | null;
  archived_by?: Id | null;
  archive_reason?: string;
  stage_entered_at?: string | null;
  next_action_at?: string | null;
  sla_overdue?: boolean;
  next_task_id?: Id | null;
  next_task_title?: string;
  next_task_due_at?: string | null;
  next_task_priority?: Task["priority"] | "";
  risk_level?: "low" | "medium" | "high";
  risk_percent?: number;
  notes: string;
  created_at: string;
  updated_at: string;
};

export type DealSummary = {
  total: number;
  open: number;
  won: number;
  lost: number;
  open_value: string;
  won_value: string;
  lost_value: string;
  lost_count: number;
  conversion_rate: number;
  stale_deals: number;
  pipeline_value: string;
  expected_revenue: string;
  overdue: number;
  no_tasks: number;
  hot: number;
  mine: number;
  by_status: Partial<Record<Deal["status"], number>>;
  by_source: Record<string, number>;
  by_stage: Record<string, number>;
};

export type Appointment = {
  responsible_user?: Id | null;
  responsible_user_name?: string;
  source_conversation?: Id | null;
  branch?: Id | null;
  branch_name?: string;
  branch_address?: string;
  booked_price?: string | null;
  booked_duration_minutes?: number | null;
  id: Id;
  business: Id;
  client: Id;
  client_name?: string;
  client_phone?: string;
  lead: Id | null;
  lead_title?: string;
  service: Id;
  service_name?: string;
  service_duration_minutes?: number;
  resource: Id | null;
  resource_name?: string | null;
  resource_type?: string | null;
  start_at: string;
  end_at: string;
  status: "created" | "confirmed" | "cancelled" | "rescheduled" | "completed" | "no_show";
  source: "website" | "telegram" | "whatsapp" | "instagram" | "manual" | "bot";
  notes: string;
  is_archived?: boolean;
  archived_at?: string | null;
  archived_by?: Id | null;
  archive_reason?: string;
  created_at: string;
  updated_at: string;
};

export type Notification = {
  id: Id;
  business: Id;
  recipient: Id | null;
  recipient_email?: string | null;
  recipient_name?: string | null;
  client: Id | null;
  client_name?: string | null;
  appointment: Id | null;
  channel: "telegram" | "whatsapp" | "email" | "sms" | "system";
  category: "sales" | "finance" | "system" | "ai_alerts" | "outreach" | "tasks";
  priority: "low" | "normal" | "high" | "urgent";
  text: string;
  send_at: string;
  status: "pending" | "sent" | "failed" | "cancelled";
  action_url: string;
  action_label: string;
  read_at: string | null;
  is_read: boolean;
  created_at: string;
  updated_at: string;
};

export type OutreachRecipient = {
  id: Id;
  campaign: Id;
  business: Id;
  client: Id;
  client_name?: string;
  client_phone?: string;
  notification: Id | null;
  notification_status?: Notification["status"];
  status: "queued" | "pending" | "sent" | "failed" | "skipped" | "cancelled";
  recipient_id: string;
  personalized_text: string;
  error: string;
  error_code: string;
  provider_result: Record<string, unknown>;
  skipped_reason: string;
  sent_at: string | null;
  created_at: string;
  updated_at: string;
};

export type OutreachConsent = {
  id: Id;
  business: Id;
  client: Id;
  client_name?: string;
  client_phone?: string;
  channel: "telegram" | "whatsapp";
  status: "opted_in" | "opted_out" | "unknown";
  source: string;
  note: string;
  evidence_json: Record<string, unknown>;
  opted_in_at: string | null;
  opted_out_at: string | null;
  created_at: string;
  updated_at: string;
};

export type DuplicateClient = {
  id: Id;
  full_name: string;
  phone: string;
  email: string;
  matched_fields: string[];
};

export type LeadDuplicateCheckResponse = DuplicateCheckResponse & {
  related_leads: Array<{
    id: Id;
    client: Id;
    status: Lead["status"];
    source: Lead["source"];
    message: string;
  }>;
};

export type CrmFunnelMetrics = {
  lead_counts: {
    total: number;
    by_source: Array<{ key: string; count: number }>;
    by_status: Array<{ key: Lead["status"] | string; count: number }>;
  };
  conversion_to_deal: {
    leads_total: number;
    deals_from_leads: number;
    rate: number;
  };
  deal_outcomes: {
    open_count: number;
    won_count: number;
    lost_count: number;
    open_value: string;
    won_value: string;
    lost_value: string;
  };
  appointments: {
    total: number;
    completed: number;
    no_show: number;
    completion_rate: number;
    no_show_rate: number;
  };
  tasks: {
    open: number;
    overdue: number;
  };
  conversations: {
    unanswered: number;
    unread: number;
    handoff_required: number;
    unread_sla_overdue: number;
    handoff_sla_overdue: number;
  };
};

export type ScopedManagerPerformance = {
  scope: "business" | "team" | "own" | "none" | string;
  totals: {
    assigned_leads: number;
    deals_from_leads: number;
    lead_to_deal_rate: number;
    won_deals: number;
    lost_deals: number;
    open_tasks: number;
    overdue_tasks: number;
  };
  rows: Array<{
    user_id: Id;
    email: string;
    full_name: string;
    role: string;
    assigned_leads: number;
    deals_from_leads: number;
    lead_to_deal_rate: number;
    won_deals: number;
    lost_deals: number;
    won_value: string;
    lost_value: string;
    appointments_completed: number;
    appointments_no_show: number;
    open_tasks: number;
    overdue_tasks: number;
  }>;
};

export type { Id } from "./core";
export type { User, CurrentUser, UserPreference, SocialIdentitySummary, EffectivePermission, BusinessMembershipSummary, BusinessCapabilitySummary, BusinessRole, RolePermission, TeamDepartment, TeamMember, BusinessInvitation } from "./identity";
export type { Business, OnboardingTemplate, OnboardingChecklistItem, OnboardingStatus, ApplyOnboardingTemplateResponse } from "./business";
export type { SubscriptionPlan, Subscription, UsageSummaryItem, EntitlementSummaryItem } from "./billing";
export type { PlatformOperationsSummary, PlatformMerchantOperations, PlatformMerchantHealth, PlatformSupportAction, PlatformSupportStep, PlatformSupportWorkflow, PlatformOverview, PlatformHealthGate, PlatformProviderRolloutCheck, PlatformOperationsHealth, PlatformMerchant, PlatformClinicService } from "./platform";
export type { Bot, BotChannel, IntegrationEventLog, ApiToken, ApiTokenCreateResponse, WebhookEndpoint, WebhookDeliveryLog, BusinessConnector, ConnectorCapability, ConnectorCredential, BusinessEvent, ConnectorSyncRun } from "./integrations";
export type { BotConversation, BotMessage, Conversation, Message, QuickReplyTemplate } from "./conversations";
export type { FileAttachment } from "./files";
export type { Client, LeadSummary, Pipeline, PipelineStage, DealBoardStage, DealBoard, Note, CrmEntityType, CrmCardActionDetail, Tag, TaggedObject, SegmentFilter, Segment, CrmCardPayload, DuplicateCheckResponse, CustomFieldDefinition, CustomFieldValue, CrmCardCustomField, LeadFormField, LeadCaptureForm, LeadFormSubmission } from "./crm";
export type { Service, Resource, WorkingHours, ScheduleException, AppointmentMessageSetting, AvailableSlot } from "./scheduling";
export type { NotificationPreference } from "./notifications";
export type { OutreachTemplate, OutreachCampaign } from "./outreach";
export type { AnalyticsEvent, ReportWidget, ScheduledReport, FinancialReport, OwnerDashboardMetrics, CrmAiInsightCard, TeamPerformanceMember, TeamPerformanceWarning, TeamPerformanceActionItem, TeamPerformanceTeam, TeamPerformanceMetrics, AnalyticsReportSummary } from "./analytics";
export type { AgentProfile, BusinessKnowledgeItem, AIToolCallLog, ApprovalRequest, AIToolDefinition, AIToolSuggestResponse } from "./ai";
export type { ActivityEvent } from "./activity";
export type { Task, TaskComment } from "./tasks";
export type { AutomationRule, AutomationTemplate, AutomationRun, AutomationConditionDraft, AutomationActionDraft, ManualAutomationRulePayload, AutomationPreview } from "./automation";
export type { ImportJob, ImportSummary } from "./imports";
export type { AuditLog, LoginHistory, SupportAccessGrant, SecurityRiskSummary } from "./security";

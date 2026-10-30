import type { Id } from "./core";
import type { CrmFunnelMetrics, ScopedManagerPerformance, Lead } from "./index";

export type AnalyticsEvent = {
  id: Id;
  business: Id;
  client: Id | null;
  event_type: string;
  source: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type ReportWidget = {
  id: Id;
  business: Id;
  key: string;
  title: string;
  widget_type: "kpi" | "table" | "funnel" | "list";
  config_json: Record<string, unknown>;
  sort_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type ScheduledReport = {
  id: Id;
  business: Id;
  name: string;
  frequency: "daily" | "weekly" | "monthly";
  recipients_json: string[];
  report_config_json: Record<string, unknown>;
  is_active: boolean;
  next_run_at: string | null;
  last_run_at: string | null;
  created_by: Id | null;
  created_by_email?: string | null;
  created_at: string;
  updated_at: string;
};

export type FinancialReport = {
  state: "unavailable" | "available" | "stale";
  reason: string | null;
  period: { start: string; end: string };
  source: { id: Id | null; name: string; provider: string } | null;
  last_successful_sync_at: string | null;
  currency: string;
  receipts: string | null;
  refunds: string | null;
  net_receipts: string | null;
  coverage?: "recorded_manual_operations";
  as_of?: string;
  last_recorded_at?: string | null;
  operation_count?: number;
};

export type OwnerDashboardMetrics = {
  business: Id;
  new_leads: number;
  total_leads: number;
  leads_by_source: Array<{ source: string; count: number }>;
  appointments_today: number;
  appointments_completed: number;
  no_show_count: number;
  conversion_lead_to_appointment: number;
  open_tasks: number;
  overdue_tasks: number;
  manager_response_time: number | null;
  financial: FinancialReport;
  operational_values: { completed_services_estimate: string; currency: string };
  revenue_estimate: null;
  sales_events_count?: number;
  revenue?: {
    today: null;
    yesterday: null;
    total_estimate: null;
    growth_percent: number | null;
  };
  business_pulse?: {
    tone: "setup" | "warning" | "attention" | "growth";
    title: string;
    text: string;
    primary_action?: { label: string; href: string };
  };
  recommendations?: Array<{
    key: string;
    title: string;
    description: string;
    priority: "high" | "medium" | "low";
    action_label: string;
    href: string;
  }>;
  quick_connect?: Array<{
    key: string;
    title: string;
    description: string;
    status: "connected" | "connect" | "beta" | "soon" | "request";
    href: string;
  }>;
  setup?: {
    score: number;
    sources: Record<string, boolean>;
  };
  data_quality?: {
    has_sales_data: boolean;
    sales_events_count: number;
    recommendation: string;
  };
  connector_health?: {
    connected: number;
    pending: number;
    error: number;
    total: number;
    failed_sync_runs?: number;
    latest_sync_at?: string | null;
    latest_event_at?: string | null;
    by_provider?: Array<{ provider: string; total: number; connected: number; pending: number; error: number }>;
  };
  crm_funnel?: CrmFunnelMetrics;
  manager_performance?: ScopedManagerPerformance;
  ai_insight_cards?: CrmAiInsightCard[];
  latest_business_events?: Array<{
    id: Id;
    event_type: string;
    source: string;
    connector: string;
    occurred_at: string;
    status: string;
    amount: null;
    financial_verification: "not_verified";
  }>;
  attention_items?: Array<{
    key: "new_leads" | "overdue_tasks" | "connector_errors" | "connector_pending" | "sales_data" | string;
    count: number;
    tone: "warning" | "danger" | "info" | string;
    href: string;
  }>;
  mobile_onboarding?: {
    headline: string;
    subtext: string;
    score: number;
    primary_action: { label: string; href: string };
    next_step_key: string;
    steps: Array<{
      key: string;
      title: string;
      description: string;
      status: "done" | "todo";
      href: string;
      cta: string;
      priority: number;
    }>;
  };
};

export type CrmAiInsightCard = {
  key: "overdue_tasks" | "unanswered_conversations" | "failed_connectors" | "appointment_no_show_rate" | "lead_to_deal_missing" | "crm_operating_norm" | "no_operational_data" | string;
  severity: "critical" | "warning" | "info" | "good" | string;
  metric_value: number;
  source_metric_keys: string[];
  source_ids: string[];
  href: string;
  no_data: boolean;
};

export type TeamPerformanceMember = {
  user: { id: Id; email: string; full_name: string };
  role: string;
  teams: Array<{ id: Id; name: string; is_lead: boolean }>;
  assigned_leads: number;
  contacted_leads: number;
  closed_leads: number;
  lost_leads: number;
  lost_without_reason: number;
  lost_reason_breakdown: Array<{ lost_reason: string; count: number }>;
  overdue_handoffs: number;
  missed_chat_handoffs: number;
  avg_response_time_minutes: number | null;
  appointments_created: number;
  appointment_conversion_rate: number;
  lost_rate: number;
  no_show_appointments: number;
  deals_won: number;
  deals_lost: number;
  sla_overdue_deals: number;
  tasks_overdue: number;
  tasks_completed: number;
  action_items: TeamPerformanceActionItem[];
};

export type TeamPerformanceWarning = {
  type: string;
  severity: "warning" | "critical" | "info";
  user_id: Id;
  message: string;
  count: number;
};

export type TeamPerformanceActionItem = {
  type: string;
  severity: "warning" | "critical" | "info";
  user_id: Id;
  title: string;
  description: string;
  route: string;
  count: number;
};

export type TeamPerformanceTeam = {
  id: Id;
  name: string;
  members_count: number;
  assigned_leads: number;
  lost_leads: number;
  overdue_handoffs: number;
  missed_chat_handoffs: number;
  tasks_overdue: number;
  sla_overdue_deals: number;
  deals_won: number;
  deals_lost: number;
  no_show_appointments: number;
  lost_rate: number;
};

export type TeamPerformanceMetrics = {
  business: Id;
  scope: "business" | "team" | "own";
  totals: {
    assigned_leads: number;
    contacted_leads: number;
    closed_leads: number;
    lost_leads: number;
    overdue_handoffs: number;
    missed_chat_handoffs: number;
    tasks_overdue: number;
    deals_won: number;
    deals_lost: number;
    sla_overdue_deals: number;
    no_show_appointments: number;
    appointment_conversion_rate: number;
    lost_rate: number;
  };
  members: TeamPerformanceMember[];
  teams: TeamPerformanceTeam[];
  warnings: TeamPerformanceWarning[];
  action_items: TeamPerformanceActionItem[];
};

export type AnalyticsReportSummary = {
  business: Id;
  financial: FinancialReport;
  period: { start: string | null; end: string | null };
  widgets: Array<Pick<ReportWidget, "id" | "key" | "title" | "widget_type" | "config_json" | "sort_order">>;
  source_roi: Array<{
    source: string;
    leads: number;
    appointments: number;
    completed_appointments: number;
    service_value_estimate: string;
    revenue_estimate: null;
    conversion_rate: number;
    roi_status: string;
  }>;
  funnel_velocity: {
    lead_statuses: Array<{ status: Lead["status"]; count: number }>;
    deal_stages: Array<{ stage: string; count: number; avg_probability: number; avg_days_in_stage: number | null }>;
    open_deals: number;
    won_deals: number;
    lost_deals: number;
    velocity_note: string;
  };
  manager_performance: Array<{
    user_id: Id;
    email: string;
    full_name: string;
    assigned_leads: number;
    appointment_leads: number;
    lost_leads: number;
    won_deals: number;
    lost_deals: number;
    open_tasks: number;
  }>;
  retention_ltv: {
    total_clients: number;
    repeat_clients: number;
    repeat_rate: number;
    average_service_value_estimate: string;
    ltv_estimate: null;
    data_quality: string;
  };
  crm_funnel?: CrmFunnelMetrics;
  manager_performance_scope?: ScopedManagerPerformance["scope"];
  scoped_manager_performance?: ScopedManagerPerformance;
  connector_health?: OwnerDashboardMetrics["connector_health"];
  ai_insight_cards?: CrmAiInsightCard[];
};

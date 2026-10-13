import type { FinancialReport, Id } from "./index";

export type AnalyticsPeriod = { start: string; end: string };
export type WorkspaceReport = "workspace_overview" | "workspace_sources" | "workspace_services" | "workspace_team" | "workspace_finance";
export type AnalyticsExportJob = {
  id: Id; status: "pending" | "running" | "succeeded" | "failed";
  download_url: string | null;
};
export type AnalyticsWorkspace = {
  business: Id;
  period: AnalyticsPeriod & { timezone: string };
  generated_at: string;
  availability: Record<"leads" | "deals" | "appointments" | "tasks" | "conversations", boolean>;
  leads: { total: number | null; converted: number | null; conversion_rate: number | null };
  deals: { won: number | null; lost: number | null; open_now: number | null };
  appointments: { total: number | null; by_status: Record<string, number> | null; no_show_rate: number | null };
  sources: { source: string; leads: number; converted: number | null; conversion_rate: number | null }[];
  services: { service_id: Id; service__name: string; total: number; completed: number; no_show: number }[];
  team: { available: boolean; scope: string; rows: {
    id: Id; name: string; role: string; leads: number | null; converted: number | null; conversion_rate: number | null;
    won: number | null; lost: number | null; open_tasks: number | null; overdue_tasks: number | null; unanswered: number | null;
  }[] };
  current: { new_leads: number | null; overdue_tasks: number | null; unanswered: number | null };
  financial: FinancialReport;
};

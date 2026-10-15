export type OperationSource = "incidents" | "connectors" | "automations" | "integrations" | "webhooks";
export type OperationFilters = {
  source: OperationSource; business?: number; search?: string; component?: string;
  freshness?: string; date_from?: string; date_to?: string; page: number; page_size: number;
};
export type OperationRow = {
  id: number; business_id: number | null; business_name: string | null; status: string;
  component?: string; episode?: number; started_at?: string; observed_at?: string;
  affected_count?: number; fresh?: boolean; linked_cases?: number | null;
  provider?: string; kind?: string; attempts?: number; max_attempts?: number; occurred_at?: string;
};
export type OperationPage = {
  count: number | null; next: string | null; previous: string | null; results: OperationRow[];
  source: OperationSource; generated_at: string; unavailable_sources: string[];
  period: { from: string; to: string; timezone: string } | null;
};

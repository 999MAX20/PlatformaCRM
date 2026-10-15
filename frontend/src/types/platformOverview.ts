import type { SupportStatus } from "./support";

export type OverviewAttention = {
  generated_at: string; preview_limit: number; unavailable_sources: string[];
  clinics: {
    count: number; degraded: number; unknown: number; links_available: boolean;
    results: Array<{ id: number; name: string; status: "degraded" | "unknown";
      degraded_components: number; unknown_components: number;
      components: Array<{ component: string; state: "degraded" | "unknown"; observed_at: string | null;
        started_at: string | null; episode: number; linked_cases: number | null }>;
    }>;
  } | null;
  support: {
    count: number; unassigned: number; waiting_clinic: number;
    results: Array<{ id: number; subject: string; business_id: number; business_name: string;
      status: SupportStatus; updated_at: string;
      assignee: { id: number; name: string; available: boolean } | null }>;
  } | null;
};

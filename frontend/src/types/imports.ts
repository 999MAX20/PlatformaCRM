import type { Id } from "./core";

export type ImportJob = {
  id: Id;
  business: Id;
  actor: Id | null;
  actor_email?: string;
  entity_type: "clients" | "leads" | "deals" | "sales" | "catalog";
  source_file: string;
  original_filename: string;
  status: "uploaded" | "previewed" | "imported" | "failed" | "cancelled";
  mapping_json: Record<string, string>;
  preview_json: {
    headers?: string[];
    rows?: Array<Record<string, string>>;
    import_summary?: ImportSummary;
  };
  duplicates_json: {
    rows?: Array<{
      row: number;
      payload: Record<string, string>;
      duplicates: Array<{ id: Id; full_name: string; phone?: string; email?: string; matched_fields: string[] }>;
    }>;
  };
  errors_json?: {
    rows?: Array<{
      row: number;
      field: string;
      message: string;
    }>;
  };
  total_rows: number;
  imported_count: number;
  summary_json?: ImportSummary;
  error: string;
  created_at: string;
  updated_at: string;
  imported_at?: string | null;
};

export type ImportSummary = {
  total_rows?: number;
  preview_rows?: number;
  errors?: number;
  duplicates?: number;
  created?: number;
  updated?: number;
  skipped?: number;
  imported?: number;
  ready?: boolean;
  status?: string;
};

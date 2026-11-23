import { apiClient } from "./client";
import type { Id, ImportJob } from "../types";

export type GoogleConnection = { id: number | null; status: string; email: string; last_sync_at?: string | null; enabled?: boolean; retention_enabled?: boolean };
export type GoogleSheet = { sheetId: number; title: string };
export type GoogleSpreadsheet = { id: string; title: string; sheets: GoogleSheet[] };
export type GoogleExport = { id: string; request_key: string; status: string; spreadsheet_id: string; row_count: number; updated_at: string };
const base = "/api/integrations/google/";
const sheets = (id: Id, operation: string) => `${base}connections/${id}/sheets/${operation}/`;

export const googleIntegrationsApi = {
  status: async (business: Id, provider = "google_sheets") => (await apiClient.get<GoogleConnection>(base, { params: { business, provider } })).data,
  start: async (business: Id, provider = "google_sheets") => (await apiClient.post<{ authorization_url: string }>(`${base}start/`, { business, provider })).data,
  complete: async (code: string, state: string) => (await apiClient.post<GoogleConnection>(`${base}complete/`, { code, state })).data,
  disconnect: async (id: Id) => (await apiClient.post<GoogleConnection & { google_revoked: boolean }>(`${base}connections/${id}/disconnect/`)).data,
  metadata: async (id: Id, file_id: string) => (await apiClient.post<GoogleSpreadsheet>(sheets(id, "metadata"), { file_id })).data,
  import: async (id: Id, file_id: string, sheet_id: number, request_key: string) => (await apiClient.post<ImportJob>(sheets(id, "import"), { file_id, sheet_id, request_key })).data,
  exports: async (id: Id) => (await apiClient.get<GoogleExport[]>(sheets(id, "exports"))).data,
  export: async (id: Id, request_key: string, refresh = false) => (await apiClient.post<GoogleExport>(sheets(id, "export"), { request_key, refresh })).data,
  picker: async (id: Id) => (await apiClient.post<{ access_token: string; api_key: string; app_id: string }>(sheets(id, "picker"))).data,
};

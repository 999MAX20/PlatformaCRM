import type { Id } from "./core";

export type FileAttachment = {
  id: Id;
  business: Id;
  uploaded_by: Id | null;
  uploaded_by_email?: string | null;
  original_name: string;
  content_type: string;
  size: number;
  entity_type: string;
  entity_id: string;
  visibility: "private";
  scan_status: "pending" | "scanning" | "clean" | "infected" | "error";
  scanned_at: string | null;
  download_url: string;
  created_at: string;
};

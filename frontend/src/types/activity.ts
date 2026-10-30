import type { Id } from "./core";

export type ActivityEvent = {
  id: Id;
  business: Id;
  client: Id | null;
  actor: Id | null;
  category: "crm" | "message" | "appointment" | "task" | "automation" | "system";
  event_type: string;
  source: string;
  entity_type: string;
  entity_id: string;
  text: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

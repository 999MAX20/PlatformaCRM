import type { ActivityEvent, Id } from "./index";
import type { PaginatedResponse } from "../api/client";

export type TimelineEvent = ActivityEvent & {
  actor_name: string;
  client_name: string;
  entity_name?: string;
  entity_available?: boolean;
  reference_names?: Partial<Record<"from_stage" | "to_stage" | "from_assignee" | "to_assignee", string>>;
};
export type TimelineFilters = {
  entity_type?: string;
  entity_id?: string;
  search: string;
  category: string;
  actor: string;
  date_from: string;
  date_to: string;
  page: number;
  page_size: number;
};
export type TimelineActor = { id: Id; name: string };
export type TimelineActorsPage = PaginatedResponse<TimelineActor> & {
  selected_actor: TimelineActor | null;
};

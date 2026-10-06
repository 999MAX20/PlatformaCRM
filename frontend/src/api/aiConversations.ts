import { apiClient } from "./client";
import type { AIToolCallLog, Id } from "../types";

export type ConversationMode = "work" | "analytics";
export type TurnStatus = "preparing" | "clarifying" | "awaiting_confirmation" | "executing" | "completed" | "failed" | "cancelled" | "superseded";
export type AgentConversation = {
  id: string; business: Id; agent: Id; title: string; is_archived: boolean;
  revision: number; memory_enabled: boolean; memory_epoch: number; status: TurnStatus | "empty"; updated_at: string;
};
export type AgentTurn = {
  id: Id; sequence: number; status: TurnStatus; mode: ConversationMode; message: string; response: string;
  redacted: boolean; sources: Array<{ id: string; label: string }>;
  actions: Array<AIToolCallLog & { fingerprint: string }>;
  error_code: string; provider_state: string; completed_steps: number; total_steps: number; created_at: string; updated_at: string;
};
export type ConversationPage = { conversation: AgentConversation; turns: AgentTurn[]; has_more: boolean; next_before: number | null };
const root = "/api/ai/conversations/";
export const aiConversationsApi = {
  async list(params: { business: Id; agent: Id; archived?: boolean; offset?: number }) {
    return (await apiClient.get<{ results: AgentConversation[]; next_offset: number | null }>(root, { params })).data;
  },
  async create(value: { business: Id; agent: Id; mode: ConversationMode }) {
    return (await apiClient.post<AgentConversation>(root, value)).data;
  },
  async get(id: string, before?: number) {
    return (await apiClient.get<ConversationPage>(`${root}${id}/`, { params: { before } })).data;
  },
  async send(id: string, value: { message: string; idempotency_key: string; mode: ConversationMode; period?: { start: string; end: string } }) {
    return (await apiClient.post<AgentTurn>(`${root}${id}/turns/`, value)).data;
  },
  async cancel(id: string, turn: Id) {
    return (await apiClient.post<AgentTurn>(`${root}${id}/turns/${turn}/cancel/`)).data;
  },
  async retry(id: string, turn: Id, idempotency_key: string) {
    return (await apiClient.post<AgentTurn>(`${root}${id}/turns/${turn}/retry/`, { idempotency_key })).data;
  },
  async confirm(id: string, turn: Id, expected_revision: number, actions: Array<{ id: Id; fingerprint: string }>) {
    return (await apiClient.post<AgentTurn>(`${root}${id}/turns/${turn}/confirm/`, { expected_revision, actions })).data;
  },
  async reset(id: string) {
    return (await apiClient.post<AgentConversation>(`${root}${id}/reset-memory/`)).data;
  },
  async archive(id: string, is_archived: boolean) {
    return (await apiClient.patch<AgentConversation>(`${root}${id}/`, { is_archived })).data;
  },
};

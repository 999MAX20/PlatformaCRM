import { apiClient } from "./client";

export type ParticipationState = "pending" | "active" | "declined" | "withdrawn" | "ended" | "revoked";
export type ParticipationScope = { business_id: number; patient_id: number };
export type ParticipationPageScope = { business_id: number; before_id?: number; limit?: number };
export type ParticipationSource =
  | { source_appointment_id: number; source_participation_id?: never }
  | { source_participation_id: number; source_appointment_id?: never }
  | { source_appointment_id?: never; source_participation_id?: never };
export type Participation = {
  id: number;
  patient_id: number;
  patient_name: string;
  branch_id: number;
  branch_name: string;
  member_id: number;
  member_name: string;
  proposed_by_id: number;
  proposer_name: string;
  state: ParticipationState;
  revision: number;
  proposed_at: string;
  accepted_at: string | null;
  closed_at: string | null;
  remaining_responsible_id: number | null;
  decline_reason: string | null;
  work_direction: string | null;
  planned_work_date: string | null;
};
export type ParticipationPage = { results: Participation[]; next_before_id: number | null };
export type ParticipationNotificationContext = {
  participation: Participation;
  direction: "incoming" | "outgoing";
  source_appointment_id: number | null;
  source_participation_id: number | null;
};
export type ProposalSourceScope = ParticipationScope & ParticipationSource;
export type ProposalBranches = { results: Array<{ id: number; name: string }>; next_after_branch_id: number | null };
export type ParticipationWorkspaceAccess = {
  business_id: number;
  member_id: number;
  kind: "doctor" | "head";
  branches: Array<{ id: number; name: string; actions: Record<"create" | "approve" | "manage" | "update", boolean> }>;
};
export type ParticipationCandidatesScope = ParticipationScope & ParticipationSource & {
  branch_id: number;
  query?: string;
  after_member_id?: number;
  limit?: number;
};
export type ParticipationCandidates = {
  results: Array<{ member_id: number; name: string }>;
  patient_revision: number;
  next_after_member_id: number | null;
};
export type ParticipationResponsibleCandidates = {
  results: Array<{ member_id: number; name: string }>;
  participation_revision: number;
  next_after_member_id: number | null;
};
export type ParticipationProposal = ParticipationScope & ParticipationSource & {
  branch_id: number;
  target_member_id: number;
  expected_patient_revision: number;
  reason?: string;
  work_direction: string;
  planned_work_date: string;
};
export type ParticipationCommand = ParticipationScope & { expected_revision: number };
export type ParticipationResult = { id: number; state: ParticipationState; revision: number; replayed: boolean };

const root = "/api/medical/participations/";

export type ParticipationClosure = { id: number; revision: number; state: ParticipationState; own: boolean; can_end: boolean; next_offset: number | null;
  obligations: { appointments: { count: number; ids: number[] }; encounters: { count: number; ids: number[] };
    documents: { count: number; items: Array<{ kind_id: number; name: string; version_id: number | null; encounter_id: number; appointment_id: number; blocker: string }> } } };

async function command(path: string, payload: object, idempotencyKey: string, signal?: AbortSignal) {
  if (!idempotencyKey.trim() || idempotencyKey.length > 128) {
    throw new Error("Medical command requires an idempotency key of at most 128 characters.");
  }
  const { data } = await apiClient.post<ParticipationResult>(path, payload, {
    headers: { "Idempotency-Key": idempotencyKey }, signal,
  });
  return data;
}

export const medicalParticipationApi = {
  closure: async (id: number, scope: ParticipationScope & { offset?: number; as_head?: boolean }, signal?: AbortSignal) =>
    (await apiClient.get<ParticipationClosure>(`${root}${id}/closure/`, { params: scope, signal })).data,
  endOwn: (id: number, payload: ParticipationCommand, idempotencyKey: string, signal?: AbortSignal) =>
    command(`${root}${id}/end-own/`, payload, idempotencyKey, signal),
  notificationContext: async (scope: { business_id: number; notification_id: number }, signal?: AbortSignal) => {
    const { data } = await apiClient.get<ParticipationNotificationContext>(`${root}notification-context/`, { params: scope, signal });
    return data;
  },
  proposalBranches: async (scope: ProposalSourceScope & { after_branch_id?: number; limit?: number }, signal?: AbortSignal) => {
    const { data } = await apiClient.get<ProposalBranches>(`${root}proposal-branches/`, { params: scope, signal });
    return data;
  },
  outgoing: async (scope: ProposalSourceScope & { before_id?: number; limit?: number }, signal?: AbortSignal) => {
    const { data } = await apiClient.get<ParticipationPage>(`${root}outgoing/`, { params: scope, signal });
    return data;
  },
  patientContext: async (scope: { business_id: number; client_id: number; branch_id: number }, signal?: AbortSignal) => {
    const { data } = await apiClient.get<ParticipationScope & { branch_id: number }>(`${root}patient-context/`, { params: scope, signal });
    return data;
  },
  access: async (businessId: number, signal?: AbortSignal) => {
    const { data } = await apiClient.get<ParticipationWorkspaceAccess>(`${root}workspace-access/`, { params: { business_id: businessId }, signal });
    return data;
  },
  mine: async (scope: ParticipationPageScope, signal?: AbortSignal) => {
    const { data } = await apiClient.get<ParticipationPage>(`${root}mine/`, { params: scope, signal });
    return data;
  },
  invitations: async (scope: ParticipationPageScope, signal?: AbortSignal) => {
    const { data } = await apiClient.get<ParticipationPage>(`${root}invitations/`, { params: scope, signal });
    return data;
  },
  managed: async (scope: ParticipationPageScope & { branch_id: number; patient_id?: number; state?: ParticipationState }, signal?: AbortSignal) => {
    const { data } = await apiClient.get<ParticipationPage>(`${root}managed/`, { params: scope, signal });
    return data;
  },
  candidates: async (scope: ParticipationCandidatesScope, signal?: AbortSignal) => {
    const { data } = await apiClient.get<ParticipationCandidates>(`${root}candidates/`, { params: scope, signal });
    return data;
  },
  responsibleCandidates: async (id: number, scope: ParticipationScope & { query?: string; after_member_id?: number; limit?: number }, signal?: AbortSignal) => {
    const { data } = await apiClient.get<ParticipationResponsibleCandidates>(`${root}${id}/responsible-candidates/`, { params: scope, signal });
    return data;
  },
  propose: (payload: ParticipationProposal, idempotencyKey: string, signal?: AbortSignal) =>
    command(root, payload, idempotencyKey, signal),
  respond: (id: number, payload: ParticipationCommand & { decision: "accept" | "decline"; reason?: string }, idempotencyKey: string, signal?: AbortSignal) =>
    command(`${root}${id}/respond/`, payload, idempotencyKey, signal),
  withdraw: (id: number, payload: ParticipationCommand, idempotencyKey: string, signal?: AbortSignal) =>
    command(`${root}${id}/withdraw/`, payload, idempotencyKey, signal),
  endByHead: (id: number, payload: ParticipationCommand & { responsible_member_id: number; reason: string }, idempotencyKey: string, signal?: AbortSignal) =>
    command(`${root}${id}/end-by-head/`, payload, idempotencyKey, signal),
};

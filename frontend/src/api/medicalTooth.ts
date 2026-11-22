import { apiClient } from "./client";
import type { ClinicalReadScope, ClinicalScope, EncounterState } from "./medicalClinical";

export type ToothObservation = {
  history_id: number;
  tooth_state_id: number;
  tooth: number;
  surface: string;
  revision: number;
  previous_id: number | null;
  encounter_id: number;
  author_id: number;
  author_name: string;
  observed_at: string;
  created_at: string;
  observation: string;
  reason: string;
  surface_protocol?: { reference: string; approval_reference: string };
};
export type ToothSnapshot = {
  as_of: string;
  observations: (ToothObservation & { current_revision: number })[];
  next_after_state_id: number | null;
};
export type ToothSnapshotScope = ClinicalReadScope & {
  as_of?: string;
  after_state_id?: number;
  limit?: number;
};
export type ToothHistory = {
  tooth_state_id: number;
  tooth: number;
  surface: string;
  current_revision: number;
  versions: (Pick<ToothObservation, "history_id" | "revision" | "previous_id" | "encounter_id" |
    "author_id" | "author_name" | "observed_at" | "created_at"> & { encounter_state: EncounterState })[];
  next_before_revision: number | null;
};
export type ToothHistoryScope = ClinicalReadScope & {
  tooth_state_id: number;
  before_revision?: number;
  limit?: number;
};
export type ToothSaveRequest = ClinicalScope & {
  encounter_id: number;
  tooth: number;
  surface?: string;
  surface_reference?: string;
  expected_patient_revision: number;
  expected_encounter_revision: number;
  expected_tooth_revision: number;
  observation: string;
  reason?: string;
  participation_id?: number;
};
export type ToothSaveResult = {
  history_id: number;
  tooth_state_id: number;
  revision: number;
  replayed: boolean;
};

export type ToothSurfaceOptions = {
  tooth: number;
  configured: boolean;
  reference: string | null;
  surfaces: { code: string; labels: Partial<Record<"ru" | "kk" | "en", string>> }[];
};

const root = "/api/medical/tooth-observations/";

export const medicalToothApi = {
  surfaceOptions: async (scope: ClinicalReadScope & { tooth: number }, signal?: AbortSignal): Promise<ToothSurfaceOptions> => {
    const { data } = await apiClient.get<ToothSurfaceOptions>(`${root}surface-options/`, { params: scope, signal });
    return data;
  },
  snapshot: async (scope: ToothSnapshotScope, signal?: AbortSignal): Promise<ToothSnapshot> => {
    const { data } = await apiClient.get<ToothSnapshot>(`${root}snapshot/`, { params: scope, signal });
    return data;
  },
  history: async (scope: ToothHistoryScope, signal?: AbortSignal): Promise<ToothHistory> => {
    const { data } = await apiClient.get<ToothHistory>(`${root}history/`, { params: scope, signal });
    return data;
  },
  version: async (historyId: number, scope: ClinicalReadScope, signal?: AbortSignal): Promise<ToothObservation> => {
    const { data } = await apiClient.get<ToothObservation>(`${root}${historyId}/`, { params: scope, signal });
    return data;
  },
  save: async (payload: ToothSaveRequest, idempotencyKey: string, signal?: AbortSignal): Promise<ToothSaveResult> => {
    if (!idempotencyKey.trim() || idempotencyKey.length > 128) {
      throw new Error("Medical command requires an idempotency key of at most 128 characters.");
    }
    const { data } = await apiClient.post<ToothSaveResult>(root, payload, {
      headers: { "Idempotency-Key": idempotencyKey }, signal,
    });
    return data;
  },
};

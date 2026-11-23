import { apiClient } from "./client";
import type { PlanStep } from "./visitPlans";

export type PatientVisitPlanPage = { results: {
  id: number; is_archived: boolean; terminated_at: string | null; created_at: string; steps: PlanStep[];
}[]; next_before_id: number | null };

export type ClinicalScope = { business_id: number; patient_id: number };
export type ClientClinicalAppointments = { results: { id: number; start_at: string; end_at: string }[]; next_before_id: number | null;
  participation?: { id: number; patient_id: number }; head_documents?: { patient_id: number } };
export type ClinicalOverview = {
  patient_id: number; patient_revision: number; full_name: string;
  identity_status: "unverified" | "verified"; date_of_birth: string | null;
  active_record: ClinicalRecord | null; latest_encounter: EncounterSummary | null;
};
export type ClinicalBasis =
  | { appointment_id: number; participation_id?: never }
  | { participation_id: number; appointment_id?: never };
export type ClinicalReadScope = ClinicalScope & ClinicalBasis;
export const clinicalFields = ["complaints", "anamnesis", "allergies", "contraindications", "examination", "diagnosis", "procedures", "plan", "epicrisis"] as const;
export type ClinicalField = typeof clinicalFields[number];
export type ClinicalVisitStep = { id: number; plan_id: number; position: number; service_name: string };
export type ClinicalPlanReadScope = ClinicalScope & { encounter_id: number } & (
  | ClinicalBasis
  | { correction_access_id: number; appointment_id?: never; participation_id?: never }
);
export type ClinicalPlanAccess = { scope: ClinicalPlanReadScope; onDenied: (cause: unknown) => void };
export type ClinicalPlanBookingAccess = { context: AppointmentClinicalContext; revision: number;
  onReload: () => void; onDenied: (cause: unknown) => void; unsaved: boolean };
export type ClinicalBookingRequest = ClinicalScope & { expected_revision: number; step_id: string;
  service_id: number; resource_id: number; branch_id: number; responsible_user_id?: number;
  expected_plan_revision?: number; start_at: string; expected_price: string | null;
  expected_duration_minutes: number; confirmed: true; notes: string };
export type ClinicalBookingResult = { version_id: number; revision: number; plan_id: number;
  visit_step_id: number; appointment_id: number; replayed: boolean };
export type ClinicalContent = Partial<Record<ClinicalField, string>> & {
  not_applicable?: Partial<Record<ClinicalField, string>>;
  plan_steps?: { id: string; description: string; visit_step?: ClinicalVisitStep; teeth?: number[] }[];
};
export type ToothPlanPage = { as_of: string; next_before_id: number | null; results: {
  id: number; step: NonNullable<ClinicalContent["plan_steps"]>[number]; version_id: number;
  revision: number; encounter_id: number; author_id: number; author_name: string; created_at: string;
}[] };
export type EncounterState = "draft" | "finalized";

export type ClinicalRecord = { id: number; number: string; opened_at: string };
export type AppointmentClinicalScope = { business_id: number; appointment_id: number };
export type AppointmentClinicalContext = {
  business_id: number;
  patient: {
    id: number;
    client_id: number;
    full_name: string;
    revision: number;
    identity_status: "unverified" | "verified";
  };
  appointment: {
    id: number;
    updated_at: string;
    branch_id: number;
    start_at: string;
    end_at: string;
  };
  active_record: ClinicalRecord | null;
  encounter: { id: number; revision: number; state: EncounterState; version_id: number } | null;
  actions: { create_record: boolean; open_encounter: boolean; save_draft: boolean };
};
export type EncounterSummary = {
  id: number;
  record_id: number;
  appointment_id: number;
  branch_id: number;
  primary_clinician_id: number;
  primary_clinician_name: string;
  branch_name: string;
  author_name: string;
  started_at: string;
  ended_at: string | null;
  state: EncounterState;
  revision: number;
  version_id: number;
  author_id: number;
};
export type ClinicalWorkspace = {
  patient_id: number;
  patient_revision: number;
  identity_status: "unverified" | "verified";
  active_record: ClinicalRecord | null;
  encounters: EncounterSummary[];
  next_before_id: number | null;
  filter_options: ClinicalHistoryOptions;
};
export type ClinicalHistoryFilters = { branch_id?: number; author_id?: number; state?: EncounterState;
  date_from?: string; date_to?: string };
export type ClinicalHistoryOptions = { branches: { id: number; name: string }[]; authors: { id: number; name: string }[] };
export type EncounterVersionMetadata = {
  version_id: number;
  revision: number;
  author_id: number;
  author_name: string;
  created_at: string;
};
export type EncounterHistory = {
  encounter_id: number;
  current_revision: number;
  state: EncounterState;
  versions: EncounterVersionMetadata[];
  next_before_revision: number | null;
};
export type EncounterVersion = EncounterVersionMetadata & {
  encounter_id: number;
  content: ClinicalContent;
  reason: string;
};
export type RecordOpenRequest = ClinicalReadScope & { number: string; expected_patient_revision: number };
export type RecordCommandResult = { id: number; patient_id: number; replayed: boolean };
export type EncounterOpenRequest = ClinicalScope & {
  record_id: number;
  appointment_id: number;
  expected_patient_revision: number;
  expected_appointment_updated_at: string;
  content?: ClinicalContent;
};
export type EncounterDraftRequest = ClinicalScope & {
  expected_revision: number;
  content: ClinicalContent;
  reason?: string;
  participation_id?: number;
};
export type EncounterCommandResult = { id: number; version_id: number; revision: number; replayed: boolean };
export type EncounterCompletion = {
  ready: boolean; missing_fields: ClinicalField[]; revision: number; appointment_updated_at: string;
  early: boolean; state: EncounterState;
  documents: { kind_id: number; name: string; version_id: number | null; ready: boolean; blocker: string | null }[];
};

const root = "/api/medical/encounters/";

async function command<T>(path: string, payload: object, idempotencyKey: string, signal?: AbortSignal): Promise<T> {
  if (!idempotencyKey.trim() || idempotencyKey.length > 128) {
    throw new Error("Medical command requires an idempotency key of at most 128 characters.");
  }
  const { data } = await apiClient.post<T>(path, payload, {
    headers: { "Idempotency-Key": idempotencyKey },
    signal,
  });
  return data;
}

export const medicalClinicalApi = {
  async completion(encounterId: number, scope: ClinicalScope, signal?: AbortSignal): Promise<EncounterCompletion> {
    return (await apiClient.get(`${root}${encounterId}/completion/`, { params: scope, signal })).data;
  },
  complete(encounterId: number, payload: ClinicalScope & { expected_revision: number; expected_appointment_updated_at: string; reason: string }, key: string, signal?: AbortSignal) {
    return command<EncounterCommandResult>(`${root}${encounterId}/complete/`, payload, key, signal);
  },
  bookPlanStep: (encounterId: number, payload: ClinicalBookingRequest, key: string, signal?: AbortSignal) =>
    command<ClinicalBookingResult>(`${root}${encounterId}/book-plan-step/`, payload, key, signal),
  toothPlan: async (scope: ClinicalReadScope & { tooth: number; as_of?: string; before_id?: number }, signal?: AbortSignal) =>
    (await apiClient.get<ToothPlanPage>(`${root}tooth-plan/`, { params: scope, signal })).data,
  visitSteps: async (scope: ClinicalPlanReadScope & { before_id?: number }, signal?: AbortSignal) =>
    (await apiClient.get<{ results: ClinicalVisitStep[]; next_before_id: number | null }>(`${root}visit-steps/`,
      { params: scope, signal })).data,
  appointmentContext: async (scope: AppointmentClinicalScope, signal?: AbortSignal) => {
    const { data } = await apiClient.get<AppointmentClinicalContext>(`${root}appointment-context/`, { params: scope, signal });
    return data;
  },
  workspace: async (scope: ClinicalReadScope & ClinicalHistoryFilters & { before_id?: number; limit?: number }, signal?: AbortSignal) => {
    const { data } = await apiClient.get<ClinicalWorkspace>(`${root}workspace/`, { params: scope, signal });
    return data;
  },
  overview: async (scope: ClinicalReadScope, signal?: AbortSignal) =>
    (await apiClient.get<ClinicalOverview>(`${root}overview/`, { params: scope, signal })).data,
  patientPlans: async (scope: ClinicalReadScope & { before_id?: number; archived: boolean }, signal?: AbortSignal) =>
    (await apiClient.get<PatientVisitPlanPage>(`${root}patient-plans/`, { params: scope, signal })).data,
  clientAppointments: async (scope: { business_id: number; branch_id: number; client_id: number; before_id?: number }, signal?: AbortSignal) =>
    (await apiClient.get<ClientClinicalAppointments>(`${root}client-appointments/`, { params: scope, signal })).data,
  history: async (encounterId: number, scope: ClinicalReadScope & { before_revision?: number; limit?: number }, signal?: AbortSignal) => {
    const { data } = await apiClient.get<EncounterHistory>(`${root}${encounterId}/revisions/`, { params: scope, signal });
    return data;
  },
  version: async (versionId: number, scope: ClinicalReadScope, signal?: AbortSignal) => {
    const { data } = await apiClient.get<EncounterVersion>(`${root}versions/${versionId}/`, { params: scope, signal });
    return data;
  },
  openRecord: (payload: RecordOpenRequest, idempotencyKey: string, signal?: AbortSignal) =>
    command<RecordCommandResult>("/api/medical/records/", payload, idempotencyKey, signal),
  openEncounter: (payload: EncounterOpenRequest, idempotencyKey: string, signal?: AbortSignal) =>
    command<EncounterCommandResult>(root, payload, idempotencyKey, signal),
  saveDraft: (encounterId: number, payload: EncounterDraftRequest, idempotencyKey: string, signal?: AbortSignal) =>
    command<EncounterCommandResult>(`${root}${encounterId}/draft/`, payload, idempotencyKey, signal),
};

import { branchesApi } from "./branches";
import { medicalClinicalApi, type ClinicalReadScope } from "./medicalClinical";
import { medicalToothApi, type ToothObservation } from "./medicalTooth";
import { normalizeAppError } from "./appError";

export async function getClientMedicalSummary(businessId: number, clientId: number, signal: AbortSignal) {
  const branches = await branchesApi.listAll({ business: businessId });
  let scope: ClinicalReadScope | undefined;
  for (const branch of branches.filter(item => item.is_active && !item.archived_at && item.can_work)) {
    if (signal.aborted) throw new DOMException("Aborted", "AbortError");
    try {
      const access = await medicalClinicalApi.clientAppointments({ business_id: businessId, client_id: clientId, branch_id: branch.id }, signal);
      if (access.participation) {
        scope = { business_id: businessId, patient_id: access.participation.patient_id, participation_id: access.participation.id };
      } else if (access.results.length) {
        const context = await medicalClinicalApi.appointmentContext({ business_id: businessId, appointment_id: access.results[0].id }, signal);
        if (context.patient.client_id !== clientId) throw new Error("Patient context mismatch");
        scope = { business_id: businessId, patient_id: context.patient.id, appointment_id: context.appointment.id };
      }
      if (scope) break;
    } catch (error) {
      if (![403, 404].includes(normalizeAppError(error).status ?? 0)) throw error;
    }
  }
  if (!scope) return null;
  const overview = await medicalClinicalApi.overview(scope, signal);
  const version = overview.latest_encounter ? await medicalClinicalApi.version(overview.latest_encounter.version_id, scope, signal) : null;
  const teeth: ToothObservation[] = [];
  let cursor: number | undefined;
  do {
    const page = await medicalToothApi.snapshot({ ...scope, after_state_id: cursor }, signal);
    teeth.push(...page.observations);
    cursor = page.next_after_state_id ?? undefined;
  } while (cursor !== undefined);
  return { overview, version, teeth };
}

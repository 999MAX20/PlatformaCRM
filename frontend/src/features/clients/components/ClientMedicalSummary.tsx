import { useQuery } from "@tanstack/react-query";
import { AlertTriangle } from "lucide-react";
import { medicalClinicalApi } from "../../../api/medicalClinical";
import { normalizeAppError } from "../../../api/appError";
import { Button } from "../../../components/ui/Button";
import { ErrorState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";

export function ClientMedicalSummary({ businessId, clientId, appointmentId, userId }: {
  businessId: number; clientId: number; appointmentId?: number; userId: number;
}) {
  const { t } = useI18n();
  const query = useQuery({
    queryKey: ["client-medical-summary", businessId, clientId, appointmentId, userId],
    enabled: Boolean(appointmentId), retry: false, staleTime: 0,
    queryFn: async ({ signal }) => {
      const context = await medicalClinicalApi.appointmentContext({ business_id: businessId, appointment_id: appointmentId! }, signal);
      if (context.patient.client_id !== clientId) throw new Error("Patient context mismatch");
      const scope = { business_id: businessId, patient_id: context.patient.id, appointment_id: appointmentId! };
      const overview = await medicalClinicalApi.overview(scope, signal);
      return overview.latest_encounter ? medicalClinicalApi.version(overview.latest_encounter.version_id, scope, signal) : null;
    },
  });
  if (!appointmentId || [401, 403, 404].includes(normalizeAppError(query.error).status || 0)) return null;
  if (query.error) return <ErrorState error={query.error} action={<Button variant="secondary" onClick={() => void query.refetch()}>{t("common.retry")}</Button>} />;
  const source = query.data;
  if (!source) return null;
  return <>{(["allergies", "contraindications"] as const).map(field => source.content[field] && source.content.not_applicable?.[field] === undefined
    ? <div key={field} className="entity-clinical-warning"><AlertTriangle size={21} aria-hidden /><p><strong>{t(`medical.clinical.${field}`)}: </strong>{source.content[field]}</p></div> : null)}</>;
}

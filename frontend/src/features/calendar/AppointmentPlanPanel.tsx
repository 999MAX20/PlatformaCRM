import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { visitPlansApi } from "../../api/visitPlans";
import { Button } from "../../components/ui/Button";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useAuth } from "../auth/AuthProvider";
import { formatDateTime } from "../../lib/format";
import { useI18n } from "../../lib/i18n";
import type { Appointment } from "../../types";

export function AppointmentPlanPanel({ appointment, timeZone }: { appointment: Appointment; timeZone: string }) {
  const { t, language } = useI18n();
  const { user } = useAuth();
  const plan = useQuery({
    queryKey: ["visit-plans", appointment.business, user?.id, appointment.visit_plan],
    queryFn: () => visitPlansApi.get(appointment.business, appointment.visit_plan!),
    enabled: !!appointment.visit_plan,
  });
  if (!appointment.visit_plan) return null;
  return <section className="space-y-3 rounded-card border border-platforma-border p-4">
    <h3 className="font-semibold">{t("plans.plan")} #{appointment.visit_plan}</h3>
    {plan.isPending ? <LoadingState /> : plan.error ? <ErrorState error={plan.error} action={<Button onClick={() => void plan.refetch()}>{t("common.retry")}</Button>} /> : <ol className="space-y-3">{plan.data?.steps.map(step => <li key={step.id} aria-current={step.appointment === appointment.id ? "step" : undefined} className="border-l-2 border-platforma-border pl-3 text-sm aria-[current=step]:border-brand-500">
      <p className="font-medium">{step.service_name}</p>
      <p>{t(step.removed_at ? "plans.removed" : !step.appointment ? "plans.unscheduled" : ["created", "rescheduled"].includes(step.status) ? "records.planned" : `status.${step.status}`)}</p>
      {step.start_at && <p>{formatDateTime(step.start_at, timeZone, true, language)}</p>}
    </li>)}</ol>}
    {plan.data && <Link className="platforma-focus-ring inline-flex rounded py-2 text-brand-700" to={`/app/appointments?view=plans&plan=${appointment.visit_plan}`}>{t("plans.plan")}</Link>}
  </section>;
}

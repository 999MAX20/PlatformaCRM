import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { branchesApi } from "../../api/branches";
import { normalizeAppError } from "../../api/appError";
import { clientsApi } from "../../api/clients";
import { teamApi } from "../../api/team";
import { visitPlansApi, type PlanResult, type PlanStep } from "../../api/visitPlans";
import { useActionFeedback } from "../../components/actions/useActionFeedback";
import { AppointmentForm } from "../../components/forms/AppointmentForm";
import { usePageHeader } from "../../components/layout/PageHeaderContext";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { Select } from "../../components/ui/Select";
import { Textarea } from "../../components/ui/Textarea";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { refreshAppointmentQueries } from "../../lib/appointmentCache";
import { formatDateTime } from "../../lib/format";
import { useI18n } from "../../lib/i18n";
import { hasPermission } from "../../lib/permissions";
import { useAuth } from "../auth/AuthProvider";
import { PlanEditor } from "./PlanEditor";
import { PlanHistory } from "./PlanHistory";
import { useCalendarCatalog } from "./useCalendarCatalog";

type Dialog = { kind: "add" | "edit" | "schedule" | "remove" | "archive" | "restore" | "responsible"; step?: PlanStep } | null;
export function VisitPlansPage() {
  const { t, language } = useI18n();
  const { user } = useAuth();
  const { business } = useActiveBusiness();
  const [params, setParams] = useSearchParams();
  const cache = useQueryClient();
  const { setPageHeader } = usePageHeader();
  const { notifyError, notifySuccess, getRecoverableMessage } = useActionFeedback();
  const [dialog, setDialog] = useState<Dialog>(null);
  const [dialogRevision, setDialogRevision] = useState<number>();
  const [reason, setReason] = useState("");
  const [consent, setConsent] = useState(false);
  const [responsible, setResponsible] = useState(0);
  const [selectedSteps, setSelectedSteps] = useState<number[]>([]);
  const [error, setError] = useState<unknown>(null);
  const attempt = useRef<{ fingerprint: string; key: string; payload: Record<string, unknown> } | null>(null);
  const [reviewCurrent, setReviewCurrent] = useState(false);
  const id = Number(params.get("plan")) || undefined;
  const clientId = Number(params.get("client")) || undefined;
  const page = Math.max(1, Number(params.get("page")) || 1);
  const createRequested = params.get("create") === "1";
  const archived = params.get("archived") === "1";
  const canCreate = hasPermission(user, business?.id, "appointments", "create");
  const creating = createRequested && canCreate;
  const catalog = useCalendarCatalog(business?.id, user?.id, false, false);
  const branches = useQuery({ queryKey: ["branches", business?.id, user?.id], queryFn: () => branchesApi.listAll({ business: business!.id }), enabled: !!business });
  const members = useQuery({ queryKey: ["team-members", "appointment", business?.id, user?.id], queryFn: () => teamApi.allMembers(business!.id), enabled: !!business && hasPermission(user, business.id, "team", "view") });
  const list = useQuery({ queryKey: ["visit-plans", "list", business?.id, user?.id, clientId, page, archived], queryFn: () => visitPlansApi.list({ business: business!.id, client: clientId, page, archived }), enabled: !!business && !id });
  const detail = useQuery({ queryKey: ["visit-plans", "detail", business?.id, user?.id, id], queryFn: () => visitPlansApi.get(business!.id, id!), enabled: !!business && !!id });
  const plan = detail.data;
  const client = useQuery({ queryKey: ["clients", "plan", business?.id, user?.id, plan?.client], queryFn: () => clientsApi.get(plan!.client), enabled: !!plan && dialog?.kind === "schedule" });
  const update = (key: string, value: string) => setParams(current => {
    const next = new URLSearchParams(current);
    if (value) next.set(key, value); else next.delete(key);
    if (key !== "page") next.delete("page");
    return next;
  });
  useEffect(() => {
    setPageHeader({ title: t("plans.title"), primaryAction: canCreate ? { label: t("plans.create"), icon: Plus, onClick: () => update("create", "1") } : undefined });
    return () => setPageHeader(null);
  }, [setPageHeader, t, canCreate, setParams]);
  useEffect(() => { setDialog(null); setError(null); attempt.current = null; }, [business?.id, user?.id, id]);
  const save = useMutation({
    mutationFn: async ({ command, payload }: { command: string; payload: Record<string, unknown> }) => {
      const { expected_revision: _revision, ...input } = payload;
      const fingerprint = JSON.stringify({ business: business!.id, actor: user?.id, id, command, input });
      if (attempt.current?.fingerprint !== fingerprint) attempt.current = { fingerprint, key: crypto.randomUUID(), payload };
      if (command === "create") return visitPlansApi.create(attempt.current.payload as Parameters<typeof visitPlansApi.create>[0], attempt.current.key);
      return visitPlansApi.command(business!.id, id!, command, attempt.current.payload, attempt.current.key);
    },
    onSuccess: async (result: PlanResult) => {
      attempt.current = null; setError(null); setDialog(null);
      await cache.invalidateQueries({ queryKey: ["visit-plans"] });
      await refreshAppointmentQueries(cache);
      setParams(current => {
        const next = new URLSearchParams(current);
        next.delete("create"); next.delete("page");
        if ("id" in result) next.set("plan", String(result.id)); else next.delete("plan");
        return next;
      });
      notifySuccess(t("common.saved"));
    },
    onError: caught => {
      const issue = normalizeAppError(caught);
      if (issue.status === 400 || ["invalid_transition", "schedule_conflict"].includes(issue.code)) attempt.current = null;
      setError(caught); notifyError(caught);
    },
  });
  const send = (command: string, payload: Record<string, unknown>) => save.mutateAsync({ command, payload }).catch(() => undefined);
  const open = (value: NonNullable<Dialog>) => { setDialog(value); setDialogRevision(plan?.revision); setReason(""); setConsent(false); setError(null); setReviewCurrent(false); setResponsible(plan?.responsible_user || 0); setSelectedSteps([]); };
  const memberOptions = [{ id: user?.id || 0, name: user?.full_name || user?.email || "" }, ...(members.data || []).filter(member => member.is_active && member.user.id !== user?.id).map(member => ({ id: member.user.id, name: member.user.full_name || member.user.email }))];
  const catalogError = catalog.services.error || catalog.resources.error || branches.error || members.error;
  const refresh = async () => {
    if (!id) { await list.refetch(); return; }
    const current = await detail.refetch();
    if (current.data) {
      setDialogRevision(current.data.revision);
      setReviewCurrent(true); setConsent(false);
      if (dialog?.step) {
        const step = current.data.steps.find(item => item.id === dialog.step!.id);
        if (step) setDialog({ ...dialog, step });
      }
    }
  };
  const recovery = error ? <ErrorState message={getRecoverableMessage(error)} action={<Button variant="secondary" onClick={refresh}>{t("common.refresh")}</Button>} /> : null;
  if (!business) return <EmptyState title={t("appointments.noBusiness")} />;
  return <div className="space-y-4" data-testid="visit-plans">
    <nav className="flex flex-wrap gap-4 text-sm"><Link className="platforma-focus-ring rounded text-brand-700" to="/app/appointments">{t("appointments.title")}</Link>{id ? <Button variant="secondary" onClick={() => update("plan", "")}>{t("plans.title")}</Button> : null}</nav>
    {id ? detail.isPending ? <LoadingState /> : detail.error ? <ErrorState message={getRecoverableMessage(detail.error)} action={<Button onClick={() => void detail.refetch()}>{t("common.retry")}</Button>} /> : plan ? <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><h2 className="text-lg font-semibold">{t("plans.plan")} #{plan.id} · {plan.client_name}</h2><p className="text-sm text-platforma-subtle">{t("appointment.responsible")}: {plan.responsible_user_name}</p></div>
        {plan.can_change ? <div className="flex flex-wrap gap-2">{!plan.is_archived ? <><Button onClick={() => open({ kind: "add" })}>{t("plans.addStep")}</Button><Button variant="secondary" onClick={() => open({ kind: "responsible" })}>{t("appointment.responsible")}</Button></> : null}<Button variant="secondary" onClick={() => open({ kind: plan.is_archived ? "restore" : "archive" })}>{t(plan.is_archived ? "plans.restore" : "plans.archive")}</Button></div> : null}
      </div>
      {recovery}
      {plan.steps.length ? <ol className="space-y-3">{plan.steps.map(step => <li key={step.id} className="rounded-card border border-platforma-border bg-white p-4">
        <div className="flex flex-wrap items-start justify-between gap-3"><div><h3 className="font-semibold">{step.service_name}</h3><p className="text-sm text-platforma-subtle">{step.removed_at ? t("plans.removed") : step.appointment ? (step.status === "created" || step.status === "rescheduled" ? t("records.planned") : t(`status.${step.status}`)) : t("plans.unscheduled")}{step.resource_name ? ` · ${step.resource_name}` : ""}</p>{step.start_at ? <p className="text-sm">{formatDateTime(step.start_at, business.timezone, false, language === "kk" ? "kk-KZ" : language === "en" ? "en-US" : "ru-RU")}</p> : null}</div>
          <div className="flex flex-wrap gap-2">{step.appointment ? <Link className="platforma-focus-ring rounded px-3 py-2 text-sm text-brand-700" state={{ recordReturnTo: `/app/appointments?${params.toString()}` }} to={`/app/appointments/${step.appointment}`}>{t("plans.openAppointment")}</Link> : !step.removed_at && !plan.is_archived && plan.can_change ? <><Button disabled={!canCreate} onClick={() => open({ kind: "schedule", step })}>{t("plans.schedule")}</Button><Button variant="secondary" onClick={() => open({ kind: "edit", step })}>{t("common.edit")}</Button><Button variant="secondary" onClick={() => open({ kind: "remove", step })}>{t("plans.remove")}</Button></> : null}</div>
        </div>
      </li>)}</ol> : <EmptyState title={t("plans.emptySteps")} />}
      <PlanHistory key={plan.id} business={business.id} actor={user?.id || 0} plan={plan.id} timeZone={business.timezone || "UTC"} />
    </> : null : <>
      <Select label={t("plans.status")} value={archived ? "1" : "0"} options={[{ value: "0", label: t("plans.active") }, { value: "1", label: t("plans.archived") }]} onChange={event => update("archived", event.target.value)} />
      {clientId ? <Button variant="secondary" onClick={() => update("client", "")}>{t("records.reset")}</Button> : null}
      {list.isPending ? <LoadingState /> : list.error ? <ErrorState message={getRecoverableMessage(list.error)} action={<Button onClick={() => void list.refetch()}>{t("common.retry")}</Button>} /> : list.data?.results.length ? <>
        <ul className="divide-y divide-platforma-border rounded-card border border-platforma-border">{list.data.results.map(item => <li key={item.id}><button type="button" className="platforma-focus-ring w-full rounded p-4 text-left hover:bg-surface-muted" onClick={() => update("plan", String(item.id))}><span className="font-semibold">{item.client_name}</span><span className="ml-3 text-sm text-platforma-subtle">{t("plans.plan")} #{item.id}</span></button></li>)}</ul>
        <div className="flex items-center justify-between gap-3"><Button variant="secondary" disabled={!list.data.previous} onClick={() => update("page", String(page - 1))}>{t("pagination.previous")}</Button><span>{page}</span><Button variant="secondary" disabled={!list.data.next} onClick={() => update("page", String(page + 1))}>{t("pagination.next")}</Button></div>
      </> : <EmptyState title={t("plans.empty")} />}
    </>}
    <Modal title={t(creating ? "plans.create" : dialog?.kind === "schedule" ? "plans.schedule" : "plans.edit")} open={creating || !!dialog} onClose={() => { if (!save.isPending) { update("create", ""); setDialog(null); setError(null); } }} size="lg">
      {recovery}
      {reviewCurrent && plan ? <div className="rounded-card border border-platforma-border p-3 text-sm"><p className="font-semibold">{t("plans.currentComposition")}</p><ul>{plan.steps.map(step => <li key={step.id}>{step.service_name} · {step.removed_at ? t("plans.removed") : step.appointment ? t(`status.${step.status}`) : t("plans.unscheduled")}</li>)}</ul></div> : null}
      {catalogError ? <ErrorState message={getRecoverableMessage(catalogError)} action={<Button onClick={() => { void catalog.services.refetch(); void catalog.resources.refetch(); void branches.refetch(); void members.refetch(); }}>{t("common.retry")}</Button>} /> : catalog.services.isPending || catalog.resources.isPending || branches.isPending ? <LoadingState /> : creating || dialog?.kind === "add" || dialog?.kind === "edit" ? <PlanEditor
        key={creating ? "create" : `${dialog?.kind}-${dialog?.step?.id}`}
        businessId={business.id} clientId={creating ? clientId : plan?.client} services={catalog.services.data || []} resources={catalog.resources.data || []} branches={branches.data || []} members={memberOptions} pending={save.isPending}
        initial={dialog?.kind === "edit" && dialog.step ? { service: dialog.step.service, resource: dialog.step.resource, branch: dialog.step.branch, responsible_user: dialog.step.responsible_user } : undefined} revision={creating ? undefined : dialogRevision}
        onSave={values => creating ? send("create", { business: business.id, client: values.client, responsible_user: values.responsible_user, steps: values.steps }) : send("revise", { expected_revision: dialogRevision, consent: values.consent, reason: values.reason, ...(dialog?.kind === "edit" ? { changes: [{ ...values.steps[0], id: dialog.step!.id }] } : { add: values.steps }) })}
      /> : dialog?.kind === "schedule" && plan && dialog.step ? client.isPending ? <LoadingState /> : client.error ? <ErrorState message={getRecoverableMessage(client.error)} action={<Button onClick={() => void client.refetch()}>{t("common.retry")}</Button>} /> : <AppointmentForm key={`${dialog.step.id}-${dialog.step.service}-${dialog.step.branch}-${dialog.step.resource}`} businessId={business.id} clients={client.data ? [client.data] : []} services={catalog.services.data || []} resources={catalog.resources.data || []} leads={[]} recordFirst fixedContext currency={business.currency} timeZone={business.timezone}
        prefill={{ client: plan.client, service: dialog.step.service, resource: dialog.step.resource, branch: dialog.step.branch, responsible_user: dialog.step.responsible_user || plan.responsible_user }}
        onSubmit={payload => send("schedule", { expected_revision: dialogRevision, step_id: dialog.step!.id, start_at: payload.start_at, resource: payload.resource, branch: payload.branch, expected_price: payload.expected_price, expected_duration_minutes: payload.expected_duration_minutes, notes: payload.notes })} /> : dialog && plan ? <form className="space-y-4" onSubmit={event => { event.preventDefault(); void send(dialog.kind === "remove" ? "revise" : dialog.kind, { expected_revision: dialogRevision, ...(dialog.kind === "responsible" ? {} : { reason }), ...(dialog.kind === "remove" ? { consent, remove: [dialog.step!.id] } : {}), ...(dialog.kind === "responsible" ? { responsible_user: responsible, step_ids: selectedSteps } : {}) }); }}>
        {dialog.kind === "responsible" ? <><Select label={t("appointment.responsible")} value={responsible} options={memberOptions.map(member => ({ value: member.id, label: member.name }))} onChange={event => setResponsible(Number(event.target.value))} />{plan.steps.filter(step => step.appointment && !step.responsible_user && ["created", "confirmed", "rescheduled"].includes(step.status)).map(step => <label key={step.id} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={selectedSteps.includes(step.id)} onChange={event => setSelectedSteps(current => event.target.checked ? [...current, step.id] : current.filter(value => value !== step.id))} />{step.service_name} · {step.start_at ? formatDateTime(step.start_at, business.timezone, false, language === "kk" ? "kk-KZ" : language === "en" ? "en-US" : "ru-RU") : ""}</label>)}</> : <Textarea label={t("plans.reason")} required maxLength={500} value={reason} onChange={event => setReason(event.target.value)} />}
        {dialog.kind === "remove" ? <label className="flex items-center gap-2 text-sm"><input type="checkbox" required checked={consent} onChange={event => setConsent(event.target.checked)} />{t("plans.consent")}</label> : null}
        <Button type="submit" isLoading={save.isPending}>{t("plans.confirm")}</Button>
      </form> : null}
    </Modal>
  </div>;
}

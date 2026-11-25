import { ArrowLeft, ArrowRight, CalendarDays, Pencil, UserRound } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useBlocker, useLocation } from "react-router";
import { Button } from "../../../components/ui/Button";
import { Tabs } from "../../../components/ui/Tabs";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import { EntityAttachmentsPanel } from "../../../components/crm/drawers/EntityAttachmentsPanel";
import { useI18n } from "../../../lib/i18n";
import { formatDateTime } from "../../../lib/format";
import type { Appointment, Client, CrmCardPayload } from "../../../types";
import { ClientPaymentsPanel } from "./ClientPaymentsPanel";
import { useAuth } from "../../auth/AuthProvider";
import { hasPermission } from "../../../lib/permissions";
import { ClientPatientOverview } from "./ClientPatientOverview";
import { usePatientRoute } from "../../medical/PatientWorkspaceScope";
import { useClientMedicalSummary } from "../hooks/useClientMedicalSummary";
import { DentalClientClinical } from "../../medical/DentalClientClinical";
import type { ClinicalEntryHandle } from "../../medical/ClinicalAppointmentEntry";
import { PatientAdministrationPanel } from "../../medical/PatientAdministrationPanel";
import { PaymentsButton } from "../../payments/PaymentsButton";
import { TasksList, TimelineList, ConversationsList } from "./ClientWorkspaceSections";
import "../../medical/entityPages.css";
import "../clientReference.css";

type Props = {
  client: Client; card: CrmCardPayload; appointments: Appointment[]; recentAppointments: Appointment[]; upcoming?: Appointment;
  editState: { dirty: boolean; pending: boolean }; medical: boolean; userId: number; timeZone: string; canEdit: boolean; canBook: boolean;
  onEdit: () => void; onTag: () => void; extraActions: React.ReactNode;
};

export function ClientReferenceView({ client, card, appointments, recentAppointments, upcoming, editState, medical, userId, timeZone, canEdit, canBook, onEdit, onTag, extraActions }: Props) {
  const { t, language } = useI18n();
  const patientPath = usePatientRoute();
  const location = useLocation();
  const { user } = useAuth();
  const canPay = hasPermission(user, client.business, "payments") && hasPermission(user, client.business, "clients");
  const summary = useClientMedicalSummary(client.business, client.id, userId, medical);
  const [tab, setTab] = useState(() => ({ timeline: "history", appointments: "visits", files: "files", tasks: "tasks", clinical: "medical" }[new URLSearchParams(location.search).get("tab") || ""] || "overview"));
  const [administrationOpen, setAdministrationOpen] = useState(false);
  const [dirty, setDirty] = useState(false);
  const clinical = useRef<ClinicalEntryHandle>(null);
  const blocker = useBlocker(dirty || editState.dirty || editState.pending);
  useEffect(() => {
    if (blocker.state !== "blocked") return;
    if (editState.pending) { blocker.reset(); return; }
    if (editState.dirty) { if (window.confirm(t("medical.clinical.discard"))) blocker.proceed(); else blocker.reset(); return; }
    let active = true;
    void (clinical.current?.beforeLeave() ?? Promise.resolve(false)).then(allowed => {
      if (active) { if (allowed) blocker.proceed(); else blocker.reset(); }
    });
    return () => { active = false; };
  }, [blocker, editState.dirty, editState.pending, t]);
  async function selectTab(next: string) {
    if (!dirty || await clinical.current?.beforeLeave()) { setDirty(false); setTab(next); if (next === "overview" && medical) void summary.refetch(); }
  }
  const returnTo = patientPath(typeof location.state?.clientReturnTo === "string" && /^\/app\/(?:clients|patients)(?:\?|$)/.test(location.state.clientReturnTo)
    ? location.state.clientReturnTo : "/app/clients");
  const options = [
    { value: "overview", label: t("crmCard.overview") },
    ...(medical ? [{ value: "medical", label: t("clients.pageMedicalTab") }] : []),
    { value: "visits", label: t("clients.pageVisits") },
    { value: "files", label: t(medical ? "medical.documents.title" : "crmCard.attachments") },
    ...(canPay ? [{ value: "payments", label: t("clients.pagePayment") }] : []),
  ];
  const panels = [...options, { value: "history", label: t("tasks.history") }, { value: "tasks", label: t("nav.tasks") }];
  const visitRows = (items: Appointment[]) => <div className="entity-visit-list">
    {items.length ? items.map(item => <Link key={item.id} to={`/app/appointments/${item.id}`} state={{ recordReturnTo: patientPath(`/app/clients/${client.id}`) }} className="entity-visit-row platforma-focus-ring">
      <span>{formatDateTime(item.start_at, timeZone, true, language)}</span>
      <span>{item.resource_name || t("appointment.noResource")}</span>
      <strong>{item.service_name || t("common.service")}</strong>
      <StatusBadge status={item.status} />
    </Link>) : <p className="entity-empty">{t("appointments.emptyTitle")}</p>}
  </div>;
  return <article className="entity-reference-page client-reference-page" data-testid="client-reference-page">
    <nav aria-label={t("common.back")} className="client-navigation"><Link to={returnTo} className="entity-back platforma-focus-ring"><ArrowLeft size={18} />{t("clients.pageBack")}</Link></nav>
    <header className="entity-identity">
      <span className="entity-avatar" aria-hidden><UserRound size={36} strokeWidth={1.7} /></span>
      <div className="entity-heading"><h1>{client.full_name}</h1><p>{medical ? t("medical.clinical.title") : t("common.client")}{medical && summary.data && !summary.error && summary.data.overview.active_record ? ` · № ${summary.data.overview.active_record.number}` : !medical ? ` · № ${client.id}` : ""}</p></div>
      <div className="entity-header-actions">
        {canEdit && <Button variant="secondary" data-testid="client-edit-action" onClick={onEdit}><Pencil size={17} />{t("clients.pageEdit")}</Button>}
        {canBook && <Link className="entity-primary platforma-focus-ring" to={`/app/appointments?create=1&client=${client.id}`}><CalendarDays size={18} />{t(medical ? "clients.pageBook" : "appointments.create")}</Link>}
      </div>
    </header>
    <Tabs value={tab} onChange={next => void selectTab(next)} options={options} appearance="underline" ariaLabel={client.full_name} idPrefix="client-page" className="entity-page-tabs" />
    {panels.map(option => <div key={option.value} role="tabpanel" id={`client-page-panel-${option.value}`} aria-label={option.label} hidden={tab !== option.value}>
      {tab === option.value && option.value === "overview" && <ClientPatientOverview client={client} appointments={recentAppointments} upcoming={upcoming} medical={medical} summary={summary} timeZone={timeZone} canBook={canBook} onMedical={() => void selectTab("medical")} onVisits={() => void selectTab("visits")} />}
      {tab === option.value && option.value === "medical" && medical && <><DentalClientClinical businessId={client.business} clientId={client.id} userId={userId} navigationRef={clinical} onDirtyChange={setDirty} /><details className="entity-administration" onToggle={event => setAdministrationOpen(event.currentTarget.open)}><summary>{t("medical.pageAdministration")}</summary>{administrationOpen && <PatientAdministrationPanel businessId={client.business} clientId={client.id} clientName={client.full_name} userId={userId} />}</details></>}
      {tab === option.value && option.value === "visits" && <section className="entity-page-section">{visitRows(appointments)}<Link className="entity-text-link" to={`/app/appointments?client=${client.id}`}>{t("clients.viewAll")}<ArrowRight size={16} /></Link><Link className="entity-text-link" to={`/app/appointments?view=plans&client=${client.id}`}>{t("plans.title")}</Link></section>}
      {tab === option.value && option.value === "files" && <>{medical && <DentalClientClinical key="documents" initialTab="documents" businessId={client.business} clientId={client.id} userId={userId} navigationRef={clinical} onDirtyChange={setDirty} />}<EntityAttachmentsPanel data={card} entity={{ type: "client", id: client.id }} readOnly={!canEdit} /></>}
      {tab === option.value && option.value === "payments" && canPay && <ClientPaymentsPanel client={client} userId={userId} timeZone={timeZone} />}
      {tab === option.value && option.value === "history" && <TimelineList cardTimeline={card.timeline} />}
      {tab === option.value && option.value === "tasks" && <TasksList tasks={card.tasks} />}
    </div>)}
    <details className="client-more"><summary>{t("clients.card.more")}</summary><div className="entity-secondary-actions"><Button variant="ghost" onClick={() => void selectTab("history")}>{t("tasks.history")}</Button><Button variant="ghost" onClick={() => void selectTab("tasks")}>{t("nav.tasks")}</Button>{canEdit && <Button variant="ghost" onClick={onTag}>{t("clients.addTag")}</Button>}<PaymentsButton client={client} />{extraActions}</div>{card.tags.length > 0 && <div className="entity-tags">{card.tags.map(tag => <span key={tag.id}>{tag.tag_name}</span>)}</div>}{card.conversations.length > 0 && <ConversationsList conversations={card.conversations} />}</details>
  </article>;
}

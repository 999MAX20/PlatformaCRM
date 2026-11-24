import { ArrowLeft, ArrowRight, CalendarDays, Mail, Pencil, Phone, UserRound } from "lucide-react";
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
import { ClientMedicalSummary } from "./ClientMedicalSummary";
import { DentalClientClinical } from "../../medical/DentalClientClinical";
import type { ClinicalEntryHandle } from "../../medical/ClinicalAppointmentEntry";
import { PatientAdministrationPanel } from "../../medical/PatientAdministrationPanel";
import { PaymentsButton } from "../../payments/PaymentsButton";
import { TasksList, TimelineList, ConversationsList } from "./ClientWorkspaceSections";
import "../../medical/entityPages.css";

type Props = {
  client: Client; card: CrmCardPayload; appointments: Appointment[]; upcoming?: Appointment;
  editState: { dirty: boolean; pending: boolean }; medical: boolean; userId: number; timeZone: string; canEdit: boolean; canBook: boolean;
  onEdit: () => void; onTag: () => void; extraActions: React.ReactNode;
};

export function ClientReferenceView({ client, card, appointments, upcoming, editState, medical, userId, timeZone, canEdit, canBook, onEdit, onTag, extraActions }: Props) {
  const { t, language } = useI18n();
  const location = useLocation();
  const { user } = useAuth();
  const canPay = hasPermission(user, client.business, "payments") && hasPermission(user, client.business, "clients");
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
    if (!dirty || await clinical.current?.beforeLeave()) { setDirty(false); setTab(next); }
  }
  const returnTo = typeof location.state?.clientReturnTo === "string" && /^\/app\/clients(?:\?|$)/.test(location.state.clientReturnTo)
    ? location.state.clientReturnTo : "/app/clients";
  const options = [
    { value: "overview", label: t("crmCard.overview") },
    ...(medical ? [{ value: "medical", label: t("medical.clinical.title") }] : []),
    { value: "visits", label: t("appointments.title") },
    { value: "files", label: t(medical ? "medical.documents.title" : "crmCard.attachments") },
    ...(canPay ? [{ value: "payments", label: t("payments.title") }] : []),
    { value: "history", label: t("tasks.history") },
    { value: "tasks", label: t("nav.tasks") },
  ];
  const visitRows = (items: Appointment[]) => <div className="entity-visit-list">
    {items.length ? items.map(item => <Link key={item.id} to={`/app/appointments/${item.id}`} state={{ recordReturnTo: `/app/clients/${client.id}` }} className="entity-visit-row platforma-focus-ring">
      <span>{formatDateTime(item.start_at, timeZone, true, language)}</span>
      <span>{item.resource_name || t("appointment.noResource")}</span>
      <strong>{item.service_name || t("common.service")}</strong>
      <StatusBadge status={item.status} />
    </Link>) : <p className="entity-empty">{t("appointments.emptyTitle")}</p>}
  </div>;
  return <article className="entity-reference-page" data-testid="client-reference-page">
    <nav aria-label={t("common.back")} className="entity-breadcrumb"><Link to={returnTo}>{t("nav.clients")}</Link><span aria-hidden>/</span><span>{client.full_name}</span></nav>
    <Link to={returnTo} className="entity-back platforma-focus-ring"><ArrowLeft size={18} />{t("common.back")}</Link>
    <header className="entity-identity">
      <span className="entity-avatar" aria-hidden><UserRound size={30} /></span>
      <div className="entity-heading"><h1>{client.full_name}</h1><p>{t("common.client")} · № {client.id}</p></div>
      <div className="entity-header-actions">
        {canEdit && <Button variant="secondary" data-testid="client-edit-action" onClick={onEdit}><Pencil size={17} />{t("clients.edit")}</Button>}
        {canBook && <Link className="entity-primary platforma-focus-ring" to={`/app/appointments?create=1&client=${client.id}`}><CalendarDays size={18} />{t("appointments.create")}</Link>}
      </div>
    </header>
    <Tabs value={tab} onChange={next => void selectTab(next)} options={options} appearance="underline" ariaLabel={client.full_name} idPrefix="client-page" className="entity-page-tabs" />
    {options.map(option => <div key={option.value} role="tabpanel" id={`client-page-panel-${option.value}`} aria-labelledby={`client-page-tab-${option.value}`} hidden={tab !== option.value}>
      {tab === option.value && option.value === "overview" && <div className="entity-page-columns">
        <div className="entity-page-main">
          {medical && <ClientMedicalSummary businessId={client.business} clientId={client.id} appointmentId={upcoming?.id || appointments[0]?.id} userId={userId} />}
          {upcoming && <section className="entity-next-visit"><CalendarDays size={27} aria-hidden /><div><p>{t("clients.card.nextAppointment")}</p><h2>{formatDateTime(upcoming.start_at, timeZone, true, language)}</h2><p>{upcoming.resource_name} · {upcoming.service_name}</p></div><Link className="entity-primary platforma-focus-ring" to={`/app/appointments/${upcoming.id}`} state={{ recordReturnTo: `/app/clients/${client.id}` }}>{t("clients.pageOpenAppointment")}<ArrowRight size={17} /></Link></section>}
          <section className="entity-page-section"><h2>{t("appointments.title")}</h2>{visitRows(appointments.slice(0, 5))}<Link className="entity-text-link" to={`/app/appointments?client=${client.id}`}>{t("appointments.title")}<ArrowRight size={16} /></Link></section>
          {medical && <section className="entity-page-section entity-medical-link"><div><h2>{t("medical.clinical.title")}</h2></div><Button variant="secondary" onClick={() => void selectTab("medical")}>{t("medical.clinical.open")}<ArrowRight size={18} /></Button></section>}
          {card.conversations.length > 0 && <section className="entity-page-section"><h2>{t("crmCard.messages")}</h2><ConversationsList conversations={card.conversations} /></section>}
        </div>
        <aside className="entity-context-panel">
          <section><h2>{t("clients.contacts")}</h2><div className="entity-contact-row"><Phone size={19} />{client.phone ? <a href={`tel:${client.phone.replace(/[^+\d]/g, "")}`}>{client.phone}</a> : <span>{t("clients.phoneMissing")}</span>}</div><div className="entity-contact-row"><Mail size={19} />{client.email ? <a href={`mailto:${client.email}`}>{client.email}</a> : <span>{t("clients.emailMissing")}</span>}</div></section>
          <section><h2>{t("clients.notes")}</h2><p className="entity-note">{client.notes || t("crmCard.noNotes")}</p>{canEdit && <Button variant="ghost" onClick={onEdit}>{t("clients.edit")}</Button>}</section>
          {(card.tags.length > 0 || canEdit) && <section><h2>{t("clients.tag")}</h2><div className="entity-tags">{card.tags.map(tag => <span key={tag.id}>{tag.tag_name}</span>)}</div>{canEdit && <Button variant="ghost" onClick={onTag}>{t("clients.addTag")}</Button>}</section>}
          <section className="entity-secondary-actions"><PaymentsButton client={client} />{extraActions}</section>
        </aside>
      </div>}
      {tab === option.value && option.value === "medical" && medical && <DentalClientClinical businessId={client.business} clientId={client.id} userId={userId} navigationRef={clinical} onDirtyChange={setDirty} />}
      {tab === option.value && option.value === "visits" && <section className="entity-page-section">{visitRows(appointments)}<Link className="entity-text-link" to={`/app/appointments?view=plans&client=${client.id}`}>{t("plans.title")}</Link></section>}
      {tab === option.value && option.value === "files" && <>{medical && <DentalClientClinical key="documents" initialTab="documents" businessId={client.business} clientId={client.id} userId={userId} navigationRef={clinical} onDirtyChange={setDirty} />}<EntityAttachmentsPanel data={card} entity={{ type: "client", id: client.id }} readOnly={!canEdit} /></>}
      {tab === option.value && option.value === "payments" && canPay && <ClientPaymentsPanel client={client} userId={userId} timeZone={timeZone} />}
      {tab === option.value && option.value === "history" && <TimelineList cardTimeline={card.timeline} />}
      {tab === option.value && option.value === "tasks" && <TasksList tasks={card.tasks} />}
    </div>)}
    {medical && tab === "overview" && <details className="entity-administration" onToggle={event => setAdministrationOpen(event.currentTarget.open)}><summary>{t("medical.pageAdministration")}</summary>{administrationOpen && <PatientAdministrationPanel businessId={client.business} clientId={client.id} clientName={client.full_name} userId={userId} />}</details>}
  </article>;
}

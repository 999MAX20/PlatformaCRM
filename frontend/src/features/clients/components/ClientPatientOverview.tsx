import { AlertTriangle, ArrowRight, CalendarDays, Mail, MessageCircle, Phone, StickyNote } from "lucide-react";
import { ClientToothPreview } from "./ClientToothPreview";
import { Link } from "react-router";
import type { Appointment, Client } from "../../../types";
import { Button } from "../../../components/ui/Button";
import { ErrorState } from "../../../components/ui/StateViews";
import { normalizeAppError } from "../../../api/appError";
import { useI18n } from "../../../lib/i18n";
import type { useClientMedicalSummary } from "../hooks/useClientMedicalSummary";

export function ClientPatientOverview({ client, appointments, upcoming, medical, summary, timeZone, canBook, onMedical, onVisits }: {
  client: Client; appointments: Appointment[]; upcoming?: Appointment; medical: boolean;
  summary: ReturnType<typeof useClientMedicalSummary>; timeZone: string; canBook: boolean;
  onMedical: () => void; onVisits: () => void;
}) {
  const { t, language } = useI18n();
  const locale = { ru: "ru-RU", kk: "kk-KZ", en: "en-GB" }[language];
  const date = (value: string, year = false) => new Intl.DateTimeFormat(locale, { day: "numeric", month: "long", ...(year ? { year: "numeric" } : {}), timeZone }).format(new Date(value));
  const time = (value: string) => new Intl.DateTimeFormat(locale, { hour: "2-digit", minute: "2-digit", timeZone }).format(new Date(value));
  const data = !medical || summary.error ? null : summary.data;
  const content = data?.version?.content;
  const completed = appointments.filter(item => item.status === "completed").sort((a, b) => Date.parse(b.start_at) - Date.parse(a.start_at)).slice(0, 3);
  const birthday = data?.overview.date_of_birth;
  const today = new Intl.DateTimeFormat("en-CA", { year: "numeric", month: "2-digit", day: "2-digit", timeZone }).format(new Date());
  const age = birthday ? Number(today.slice(0, 4)) - Number(birthday.slice(0, 4)) - Number(today.slice(5) < birthday.slice(5)) : null;
  const ageLabel = age !== null && age >= 0 ? new Intl.NumberFormat(locale, { style: "unit", unit: "year", unitDisplay: "long" }).format(age) : "";
  const channels = [client.whatsapp_id && "WhatsApp", client.telegram_id && "Telegram", client.instagram_id && "Instagram"].filter(Boolean);
  const denied = [401, 403, 404].includes(normalizeAppError(summary.error).status ?? 0);
  return <div className="entity-page-columns client-overview-columns">
    <div className="entity-page-main">
      {summary.error && !denied && <ErrorState error={summary.error} action={<Button variant="secondary" onClick={() => void summary.refetch()}>{t("common.retry")}</Button>} />}
      {(["allergies", "contraindications"] as const).map(field => content?.[field] && content.not_applicable?.[field] === undefined ?
        <div key={field} className="entity-clinical-warning" role="note"><AlertTriangle size={30} strokeWidth={1.7} /><p><strong>{t(`medical.clinical.${field}`)}: {content[field]}</strong></p></div> : null)}
      <section className="entity-next-visit">
        <span className="client-next-icon"><CalendarDays size={34} strokeWidth={1.7} /></span>
        <div><p>{t(medical ? "clients.pageNextVisit" : "clients.card.nextAppointment")}</p>{upcoming ? <><h2>{date(upcoming.start_at)} · {time(upcoming.start_at)}–{time(upcoming.end_at)}</h2><p>{[upcoming.resource_name, upcoming.service_name].filter(Boolean).join(" · ")}</p></> : <p className="client-no-visit">{t("clients.card.noUpcoming")}</p>}</div>
        {upcoming ? <Link className="entity-primary platforma-focus-ring" to={`/app/appointments/${upcoming.id}`} state={{ recordReturnTo: `/app/clients/${client.id}` }}>{t(medical ? "clients.pageOpenAppointment" : "common.open")}</Link> : canBook && <Link className="entity-primary platforma-focus-ring" to={`/app/appointments?create=1&client=${client.id}`}>{t("appointments.create")}</Link>}
      </section>
      <section className="client-recent-section"><h2>{t("clients.pageRecentVisits")}</h2>
        {completed.length ? <div className="client-recent-table"><table><thead><tr><th>{t("appointment.date")}</th><th>{t("appointment.resource")}</th><th>{t("appointment.service")}</th></tr></thead><tbody>{completed.map(item => <tr key={item.id}><td><Link to={`/app/appointments/${item.id}`} state={{ recordReturnTo: `/app/clients/${client.id}` }}>{date(item.start_at, true)}</Link></td><td>{item.resource_name || "—"}</td><td>{item.service_name || "—"}</td></tr>)}</tbody></table></div> : <p className="entity-empty">{t("clients.pageNoCompleted")}</p>}
        {completed.length > 0 && <button type="button" className="client-all-visits platforma-focus-ring" onClick={onVisits}>{t("clients.viewAll")}<ArrowRight size={16} /></button>}
      </section>
      {medical && <section className="client-medical-summary"><header><h2>{t("medical.clinical.title")}</h2><button type="button" className="platforma-focus-ring" onClick={onMedical}>{t("medical.clinical.open")}<ArrowRight size={20} /></button></header>
        {summary.isFetching && !data ? <p role="status" className="entity-empty">{t("common.loading")}</p> : data ? <div className="client-medical-details"><dl>
          <div><dt>{t("medical.clinical.diagnosis")}</dt><dd>{content?.diagnosis || t("medical.clinical.notRecorded")}</dd></div>
          <div><dt>{t("medical.page.plan")}</dt><dd>{content?.plan_steps?.map(step => step.description).join("; ") || content?.plan || t("medical.clinical.notRecorded")}</dd></div>
          <div><dt>{t("clients.pageUpdated")}</dt><dd>{data.version ? date(data.version.created_at, true) : "—"}</dd></div>
        </dl><button type="button" className="client-chart-preview platforma-focus-ring" aria-label={t("medical.clinical.open")} onClick={onMedical}><ClientToothPreview observations={data.teeth} /><span>{t("medical.tooth.title")}{data.teeth.length > 0 ? ` · ${new Set(data.teeth.map(item => item.tooth)).size}` : ""}</span></button></div> : <p className="entity-empty">{t("medical.clientEntry.empty")}</p>}
      </section>}
    </div>
    <aside className="entity-context-panel client-contact-panel"><section><h2>{t("clients.pageContacts")}</h2>
      <div className="entity-contact-row"><Phone size={23} strokeWidth={1.7} />{client.phone ? <a href={`tel:${client.phone.replace(/[^+\d]/g, "")}`}>{client.phone}</a> : <span>{t("clients.phoneMissing")}</span>}</div>
      {birthday && <div className="entity-contact-row"><CalendarDays size={23} strokeWidth={1.7} /><span>{date(`${birthday}T12:00:00Z`, true)}{ageLabel ? ` · ${ageLabel}` : ""}</span></div>}
      {client.email && <div className="entity-contact-row"><Mail size={23} strokeWidth={1.7} /><a href={`mailto:${client.email}`}>{client.email}</a></div>}
      {channels.length > 0 && <div className="entity-contact-row"><MessageCircle size={23} strokeWidth={1.7} /><span>{channels.join(", ")}</span></div>}
    </section><section><h2>{t("clients.notes")}</h2><div className="client-note-row"><StickyNote size={23} strokeWidth={1.7} /><p className="entity-note">{client.notes || t("clients.pageNoVisibleNotes")}</p></div></section></aside>
  </div>;
}

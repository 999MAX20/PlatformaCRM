import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ExternalLink } from "lucide-react";
import { useId, useRef, useState } from "react";
import { Link, useNavigate } from "react-router";
import { normalizeAppError } from "../../../api/appError";
import { crmCardsApi } from "../../../api/crmCards";
import { useAuth } from "../../../features/auth/AuthProvider";
import { VoiceAssistantTrigger } from "../../../features/voice/VoiceAssistantTrigger";
import { useActiveBusiness } from "../../../hooks/useBusiness";
import { dateInTimeZone, formatDateTime } from "../../../lib/format";
import { useI18n } from "../../../lib/i18n";
import { hasPermission } from "../../../lib/permissions";
import { useActionConfirm } from "../../actions/ActionConfirmProvider";
import { DraftGuard } from "../../actions/DraftGuard";
import { Button } from "../../ui/Button";
import { Dialog } from "../../ui/Overlay";
import { EntityCardTabs } from "../EntityCardTabs";
import { ErrorState, LoadingState } from "../../ui/StateViews";
import { EntityAttachmentsPanel } from "../drawers/EntityAttachmentsPanel";
import { EntityConversationsPanel } from "../drawers/EntityConversationsPanel";
import { CustomFieldsEditor } from "../drawers/EntityCustomFieldsPanel";
import { EntityNotesPanel } from "../drawers/EntityNotesPanel";
import { EntityTasksPanel } from "../drawers/EntityTasksPanel";
import { EntityTimeline } from "../drawers/EntityTimeline";
import type { CrmDrawerEntity } from "../drawers/types";
import { AppointmentCardActions } from "./AppointmentCardActions";
import { AppointmentCardOverview } from "./AppointmentCardOverview";

type Tab = "overview" | "timeline" | "tasks" | "files" | "notes" | "messages" | "details";
const labels: Record<Tab, string> = { overview: "crmCard.overview", timeline: "crmCard.timeline", tasks: "crmCard.tasks", files: "crmCard.attachments", notes: "crmCard.notes", messages: "crmCard.messages", details: "crmCard.customFields" };

export function AppointmentCardModal({ entity, onClose, onOpenEntity, onBack }: {
  entity: CrmDrawerEntity; onClose: () => void; onOpenEntity: (entity: CrmDrawerEntity) => void; onBack?: () => void;
}) {
  const { business } = useActiveBusiness();
  const { user } = useAuth();
  const { t, language } = useI18n();
  const zone = business?.timezone || "UTC";
  const confirm = useActionConfirm();
  const navigate = useNavigate();
  const id = useId();
  const [tab, setTab] = useState<Tab>(entity.initialTab && entity.initialTab in labels ? entity.initialTab as Tab : "overview");
  const [dirty, setDirty] = useState(false);
  const [panelPending, setPanelPending] = useState(false);
  const [actionPending, setActionPending] = useState(false);
  const [revision, setRevision] = useState(0);
  const confirming = useRef(false);
  const pending = panelPending || actionPending;
  const query = useQuery({ queryKey: ["crm-card", "appointment", entity.id, business?.id, user?.id], queryFn: () => crmCardsApi.get({ type: "appointment", id: entity.id, business: business?.id }), enabled: !!business && !!user, staleTime: 0 });
  const concealed = query.error && ["authentication", "permission", "not_found"].includes(normalizeAppError(query.error).category);
  const data = concealed ? undefined : query.data;
  const appointment = data?.appointment;
  const canEdit = !!appointment && !appointment.is_archived && data?.available_action_details?.some(action => action.id === "add_note" && action.allowed) === true;
  const primary = (["overview", "timeline", "tasks"] as const).filter(value => value !== "tasks" || hasPermission(user, business?.id, "tasks", "view"));
  const secondary = (["files", "notes", "details", "messages"] as const).filter(value => value !== "messages" || hasPermission(user, business?.id, "conversations", "view"));
  async function attempt(action: () => void) {
    if (pending || confirming.current) return;
    if (dirty) {
      confirming.current = true;
      const result = await confirm({ title: t("taskWorkspace.discardTitle"), confirmLabel: t("taskWorkspace.discard"), cancelLabel: t("taskWorkspace.keepEditing"), tone: "warning" });
      confirming.current = false;
      if (!result.confirmed) return;
      setRevision(value => value + 1);
    }
    setDirty(false); action();
  }
  const changeTab = (next: Tab) => { if (next !== tab) void attempt(() => setTab(next)); };
  const panel = data && appointment ? tab === "overview" ? <AppointmentCardOverview data={data} timeZone={zone} canEdit={canEdit && !query.isError} onDirtyChange={setDirty} onPendingChange={setPanelPending} onHistory={() => changeTab("timeline")} />
    : tab === "timeline" ? <EntityTimeline data={data} locale={language} timeZone={zone} />
    : tab === "tasks" ? <EntityTasksPanel data={data} entity={entity} />
    : tab === "files" ? <EntityAttachmentsPanel data={data} entity={entity} readOnly={!canEdit || query.isError} onDirtyChange={setDirty} onPendingChange={setPanelPending} />
    : tab === "notes" ? <EntityNotesPanel data={data} entity={entity} readOnly={!canEdit || query.isError} onDirtyChange={setDirty} onPendingChange={setPanelPending} locale={language} timeZone={zone} />
    : tab === "messages" ? <EntityConversationsPanel data={data} />
    : <CustomFieldsEditor fields={data.custom_fields.filter(field => (field.definition.options_json.display as { in_card?: boolean } | undefined)?.in_card !== false)} entity={{ type: "appointment", id: entity.id }} businessId={appointment.business} readOnly={!canEdit || query.isError} onDirtyChange={setDirty} onPendingChange={setPanelPending} /> : null;
  return <>
    {(dirty || pending) && <DraftGuard dirty={dirty} pending={pending} />}
    <Dialog open presentation="entity" size="xl" className="[&_button:not(:disabled)]:cursor-pointer [&>header]:grid [&>header]:h-auto [&>header]:min-h-16 [&>header]:grid-cols-[1fr_auto_auto] [&>header]:py-3 md:[&>header]:grid-cols-[1fr_auto_auto_auto] [&>header>div]:contents [&>header>div>button:last-child]:col-start-3 [&>header>div>button:last-child]:row-start-1 md:[&>header>div>button:last-child]:col-start-4" testId="crm-entity-drawer" title={t("crmCard.appointmentNumber", { id: entity.id })} onClose={() => void attempt(onClose)}
      headerActions={<>{data && appointment && <div className="col-span-3 row-start-2 flex flex-wrap items-center gap-2 md:col-span-1 md:col-start-2 md:row-start-1"><AppointmentCardActions data={data} timeZone={zone} disabled={dirty || panelPending || query.isError} onPendingChange={setActionPending} />
            {data.client && !data.client.is_archived && data.available_action_details?.some(action => action.id === "repeat" && action.allowed) && <Button variant="secondary" disabled={pending || query.isError} onClick={() => void attempt(() => navigate(`/app/appointments?create=1&client=${data.client!.id}&service=${appointment.service}&resource=${appointment.resource || ""}&branch=${appointment.branch || ""}`))}>{t("appointments.repeatBooking")}</Button>}</div>}<div className="col-start-2 row-start-1 flex items-center gap-3 md:col-start-3">{onBack && <Button variant="ghost" aria-label={t("common.back")} disabled={pending} onClick={() => void attempt(onBack)}><ArrowLeft size={18} /></Button>}{appointment && <>
        {!query.isError && <VoiceAssistantTrigger currentEntity={{ entity: "appointments", id: appointment.id }} />}
        <Link className="platforma-focus-ring inline-flex min-h-10 items-center gap-2 rounded-control text-sm" to={`/app/appointments/${entity.id}`} aria-label={t("clients.card.openPage")}><ExternalLink size={18} /><span className="hidden sm:inline">{t("clients.card.openPage")}</span></Link></>}</div></>}
    >
      {query.isPending ? <div className="p-6"><LoadingState /></div> : !appointment || !data ? <div className="p-6">{query.error ? <ErrorState error={query.error} action={<Button onClick={() => void query.refetch()}>{t("common.retry")}</Button>} /> : t("crmCard.loadError")}</div> : <>
        {query.error && <div className="px-6 pt-4"><ErrorState error={query.error} action={<Button onClick={() => void query.refetch()}>{t("common.retry")}</Button>} /></div>}
        <div className="grid shrink-0 gap-6 p-4 sm:p-6 md:min-h-0 md:flex-1 md:grid-cols-[240px_minmax(0,1fr)] md:grid-rows-[minmax(0,1fr)]">
          <aside className="min-w-0 border-b border-platforma-border pb-5 md:min-h-0 md:overflow-y-auto md:border-b-0 md:border-r md:pb-0 md:pr-6">
            <div className="mb-7"><h2 className="break-words text-2xl font-semibold">{data.client ? <button type="button" className="platforma-focus-ring rounded-control text-left" onClick={() => void attempt(() => onOpenEntity({ type: "client", id: data.client!.id }))}>{data.client.full_name}</button> : appointment.client_name || t("common.client")}</h2><p className="mt-2 text-base"><span className="block">{new Intl.DateTimeFormat(language === "kk" ? "kk-KZ" : language === "ru" ? "ru-RU" : "en-GB", { day: "2-digit", month: language === "kk" ? "2-digit" : "short", year: "numeric", timeZone: zone }).format(new Date(appointment.start_at))}</span><span className="block">{new Intl.DateTimeFormat(language === "kk" ? "kk-KZ" : language === "ru" ? "ru-RU" : "en-GB", { hour: "2-digit", minute: "2-digit", hourCycle: "h23", timeZone: zone }).format(new Date(appointment.start_at))} – {dateInTimeZone(appointment.start_at, zone) === dateInTimeZone(appointment.end_at, zone) ? new Intl.DateTimeFormat(language === "kk" ? "kk-KZ" : language === "ru" ? "ru-RU" : "en-GB", { hour: "2-digit", minute: "2-digit", hourCycle: "h23", timeZone: zone }).format(new Date(appointment.end_at)) : formatDateTime(appointment.end_at, zone, true, language)}</span></p></div>
            <dl className="space-y-5 text-sm">
              {data.client && (data.client.phone || data.client.email) && <div><dt className="mb-1 text-platforma-subtle">{t("clients.contacts")}</dt><dd>
                {data.client.phone && <a className="platforma-focus-ring block break-all rounded-control" href={`tel:${data.client.phone}`}>{data.client.phone}</a>}
                {data.client.email && <a className="platforma-focus-ring mt-2 block break-all rounded-control" href={`mailto:${data.client.email}`}>{data.client.email}</a>}</dd></div>}
              {[["appointment.service", appointment.service_name || `#${appointment.service}`], ["appointment.resource", appointment.resource_name || (appointment.resource ? `#${appointment.resource}` : t("appointment.noResource"))], ["appointment.responsible", appointment.responsible_user_name || t("taskWorkspace.unassigned")], ["records.branch", appointment.branch_name], ["appointment.source", t(`appointment.source.${appointment.source}`)]].filter(([, value]) => value).map(([label, value]) => <div key={label}><dt className="mb-1 text-platforma-subtle">{t(label!)}</dt><dd className="break-words font-medium">{value}</dd></div>)}
              <div><dt className="mb-1 text-platforma-subtle">{t("appointment.status")}</dt><dd><span className="font-medium">{t(`status.${appointment.status}`)}</span>{appointment.is_archived && <span className="ml-3">{t("clients.card.archived")}</span>}</dd></div>
            </dl>
          </aside>
          <div className="min-w-0 md:flex md:min-h-0 md:flex-col">
            <EntityCardTabs id={id} tabs={[...primary, ...secondary]} active={tab} labels={labels} onChange={changeTab} />
            <div key={tab} role="tabpanel" id={`${id}-panel`} aria-label={t(labels[tab])} tabIndex={0} className="platforma-focus-ring rounded-control md:min-h-0 md:flex-1 md:overflow-y-auto md:[scrollbar-gutter:stable]" data-testid="crm-entity-drawer-content">
              {tab === "notes" && data.meta?.has_more.notes && <p className="mb-4 text-sm text-platforma-subtle">{t("clients.card.limited")} <Link className="platforma-focus-ring rounded-control text-brand-700 underline" to={`/app/appointments/${appointment.id}`}>{t("clients.card.openPage")}</Link></p>}
              <div key={`${tab}:${revision}`}>{panel}</div>
            </div>
          </div>
        </div>
      </>}
    </Dialog>
  </>;
}

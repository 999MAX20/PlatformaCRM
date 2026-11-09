import { useQuery } from "@tanstack/react-query";
import { Archive, ArrowLeft, ExternalLink, Mail, MessageCircle, Pencil, Phone, Plus, Tag, UserRound } from "lucide-react";
import { useId, useRef, useState } from "react";
import { Link, useNavigate } from "react-router";
import { crmCardsApi } from "../../../api/crmCards";
import { normalizeAppError } from "../../../api/appError";
import { useAuth } from "../../../features/auth/AuthProvider";
import { VoiceAssistantTrigger } from "../../../features/voice/VoiceAssistantTrigger";
import { PaymentsButton } from "../../../features/payments/PaymentsButton";
import { useActiveBusiness } from "../../../hooks/useBusiness";
import { useI18n } from "../../../lib/i18n";
import { hasPermission } from "../../../lib/permissions";
import { DraftGuard } from "../../actions/DraftGuard";
import { useActionConfirm } from "../../actions/ActionConfirmProvider";
import { ActionMenu, type ActionMenuItem } from "../../ui/ActionMenu";
import { Button } from "../../ui/Button";
import { Dialog } from "../../ui/Overlay";
import { ErrorState, LoadingState } from "../../ui/StateViews";
import type { ClientDrawerActions } from "../CrmEntityDrawer";
import { EntityAppointmentsPanel } from "../drawers/EntityAppointmentsPanel";
import { EntityAttachmentsPanel } from "../drawers/EntityAttachmentsPanel";
import { EntityConversationsPanel } from "../drawers/EntityConversationsPanel";
import { EntityCardTabs } from "../EntityCardTabs";
import { EntityNotesPanel } from "../drawers/EntityNotesPanel";
import { EntityTasksPanel } from "../drawers/EntityTasksPanel";
import { EntityTimeline } from "../drawers/EntityTimeline";
import type { CrmCardTab, CrmDrawerEntity } from "../drawers/types";
import { ClientCardDetails } from "./ClientCardDetails";
import { ClientCardOverview } from "./ClientCardOverview";

type ClientTab = Exclude<CrmCardTab, "deals"> | "details";
const allTabs = ["overview", "timeline", "appointments", "tasks", "messages", "notes", "files", "details"] as const;
const labels: Record<ClientTab, string> = {
  overview: "crmCard.overview", timeline: "crmCard.timeline", appointments: "nav.appointments",
  tasks: "crmCard.tasks", messages: "crmCard.messages", notes: "crmCard.notes",
  files: "crmCard.attachments", details: "clients.details",
};

export function ClientCardModal({ entity, onClose, actions, onOpenEntity, onBack }: {
  entity: CrmDrawerEntity; onClose: () => void; actions?: ClientDrawerActions;
  onOpenEntity?: (entity: CrmDrawerEntity) => void; onBack?: () => void;
}) {
  const { t, language } = useI18n();
  const { business } = useActiveBusiness();
  const { user } = useAuth();
  const navigate = useNavigate();
  const confirm = useActionConfirm();
  const id = useId();
  const [tab, setTab] = useState<ClientTab>(entity.initialTab && entity.initialTab !== "deals" ? entity.initialTab : "overview");
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [pending, setPending] = useState(false);
  const [revision, setRevision] = useState(0);
  const confirming = useRef(false);
  const query = useQuery({
    queryKey: ["crm-card", "client", entity.id, business?.id, user?.id],
    queryFn: () => crmCardsApi.get({ type: "client", id: entity.id, business: business?.id }),
    enabled: Boolean(business && user),
    staleTime: 0,
  });
  // Access loss conceals cached data; transient refresh errors must not unmount drafts.
  const conceal = query.error && ["authentication", "permission", "not_found"].includes(normalizeAppError(query.error).category);
  const data = conceal ? undefined : query.data;
  const client = data?.client;
  const canEdit = !client?.is_archived && data?.available_action_details?.some(action => action.id === "add_note" && action.allowed) === true;
  const canBook = !client?.is_archived && data?.available_action_details?.some(action => action.id === "create_appointment" && action.allowed) === true;
  const visibleTabs = allTabs.filter(value => value !== "appointments" || hasPermission(user, business?.id, "appointments", "view"))
    .filter(value => value !== "tasks" || hasPermission(user, business?.id, "tasks", "view"))
    .filter(value => value !== "messages" || hasPermission(user, business?.id, "conversations", "view"));

  async function attempt(action: () => void) {
    if (pending || confirming.current) return;
    if (dirty) {
      confirming.current = true;
      const result = await confirm({ title: t("taskWorkspace.discardTitle"), confirmLabel: t("taskWorkspace.discard"), cancelLabel: t("taskWorkspace.keepEditing"), tone: "warning" });
      confirming.current = false;
      if (!result.confirmed) return;
      setRevision(value => value + 1);
    }
    setDirty(false);
    action();
  }
  const changeTab = (value: ClientTab) => { if (value !== tab) void attempt(() => setTab(value)); };
  const menu: ActionMenuItem[] = [];
  if (client) {
    if (canEdit && actions?.onEdit) menu.push({ key: "edit", label: t("clients.edit"), icon: Pencil, onSelect: () => void attempt(() => actions.onEdit?.(client)) });
    if (canEdit && actions?.onAddTag) menu.push({ key: "tag", label: t("clients.addTag"), icon: Tag, onSelect: () => void attempt(() => actions.onAddTag?.(client)) });
    if (client.phone) menu.push({ key: "call", label: t("crmCard.call"), icon: Phone, onSelect: () => { window.location.href = `tel:${client.phone}`; } });
    const phone = client.phone?.replace(/\D/g, "");
    if (phone) menu.push({ key: "whatsapp", label: "WhatsApp", icon: MessageCircle, onSelect: () => { window.open(`https://wa.me/${phone}`, "_blank", "noopener,noreferrer"); } });
    if (client.email) menu.push({ key: "email", label: "Email", icon: Mail, onSelect: () => { window.location.href = `mailto:${client.email}`; } });
    if (!client.is_archived && actions?.onArchive && hasPermission(user, client.business, "clients", "delete")) menu.push({ key: "archive", label: t("clients.archiveAction"), icon: Archive, tone: "warning", separatorBefore: true, onSelect: () => void attempt(() => actions.onArchive?.(client)) });
  }
  const counts = data?.meta?.related_counts;
  const limited = tab === "tasks" ? data?.meta?.has_more.tasks : tab === "appointments" ? data?.meta?.has_more.appointments : tab === "messages" ? data?.meta?.has_more.conversations : tab === "notes" ? data?.meta?.has_more.notes : false;
  const openAppointment = onOpenEntity ? (id: number) => void attempt(() => onOpenEntity({ type: "appointment", id })) : undefined;
  const panel = data && client ? tab === "overview" ? <ClientCardOverview data={data} onHistory={() => changeTab("timeline")} onOpenAppointment={openAppointment} />
    : tab === "timeline" ? <EntityTimeline data={data} locale={language} timeZone={business?.timezone} />
    : tab === "appointments" ? <EntityAppointmentsPanel data={data} locale={language} timeZone={business?.timezone} onOpenAppointment={openAppointment} />
    : tab === "tasks" ? <EntityTasksPanel data={data} entity={entity} />
    : tab === "messages" ? <EntityConversationsPanel data={data} />
    : tab === "notes" ? <EntityNotesPanel data={data} entity={entity} readOnly={!canEdit} onDirtyChange={setDirty} onPendingChange={setPending} locale={language} timeZone={business?.timezone} />
    : tab === "files" ? <EntityAttachmentsPanel data={data} entity={entity} readOnly={!canEdit} onDirtyChange={setDirty} onPendingChange={setPending} />
    : <ClientCardDetails data={data} entity={entity} canEdit={canEdit} onDirtyChange={setDirty} onPendingChange={setPending} /> : null;
  return <>
    {(dirty || pending) ? <DraftGuard dirty={dirty} pending={pending} /> : null}
    <Dialog open title={t("common.client")} onClose={() => void attempt(onClose)} presentation="entity" size="xl"
      className="[&_button:not(:disabled)]:cursor-pointer [&>header]:grid [&>header]:h-auto [&>header]:min-h-16 [&>header]:grid-cols-[1fr_auto_auto] [&>header]:py-3 lg:[&>header]:grid-cols-[1fr_auto_auto_auto] [&>header>div]:contents [&>header>div>button:last-child]:col-start-3 [&>header>div>button:last-child]:row-start-1 lg:[&>header>div>button:last-child]:col-start-4" testId="crm-entity-drawer"
      headerActions={<>{client && <div className="col-span-3 row-start-2 flex flex-wrap items-center gap-2 lg:col-span-1 lg:col-start-2 lg:row-start-1">            {canBook ? <Button onClick={() => void attempt(() => navigate(`/app/appointments?create=1&client=${client.id}`))}><Plus size={18} />{t("conversations.bookClient")}</Button> : null}
            {data?.conversations.length && hasPermission(user, client.business, "conversations", "view") ? <Button variant="secondary" aria-label={t("clients.card.write")} onClick={() => void attempt(() => navigate(`/app/conversations?conversation=${data.conversations[0].id}`))}><MessageCircle size={18} /><span className="hidden sm:inline">{t("clients.card.write")}</span></Button> : client.phone ? <Button variant="secondary" aria-label={t("clients.card.write")} onClick={() => window.open(`https://wa.me/${client.phone.replace(/\D/g, "")}`, "_blank", "noopener,noreferrer")}><MessageCircle size={18} /><span className="hidden sm:inline">{t("clients.card.write")}</span></Button> : client.email ? <Button variant="secondary" aria-label={t("clients.card.write")} onClick={() => { window.location.href = `mailto:${client.email}`; }}><Mail size={18} /><span className="hidden sm:inline">{t("clients.card.write")}</span></Button> : null}
            {menu.length ? <ActionMenu label={t("clients.card.actions")} items={menu} overlay="modal" /> : null}</div>}<div className="col-start-2 row-start-1 flex items-center gap-3 lg:col-start-3">
        {onBack && <Button variant="ghost" aria-label={t("common.back")} disabled={pending} onClick={() => void attempt(onBack)}><ArrowLeft size={18} /></Button>}
        {client ? <>
        {!query.isError && <VoiceAssistantTrigger currentEntity={{ entity: "clients", id: client.id }} />}
        <Link className="platforma-focus-ring inline-flex min-h-10 items-center gap-2 rounded-control text-sm" to={`/app/clients/${client.id}`} aria-label={t("clients.card.openPage")}><ExternalLink size={18} /><span className="hidden sm:inline">{t("clients.card.openPage")}</span></Link></> : null}</div></>}
    >
      {query.isPending ? <div className="p-6"><LoadingState /></div> : query.error && !client ? <div className="p-6"><ErrorState error={query.error} action={<Button variant="secondary" onClick={() => void query.refetch()}>{t("common.retry")}</Button>} /></div> : !client ? <p className="p-6">{t("crmCard.loadError")}</p> : <>
        {query.error ? <div className="px-6 pt-4"><ErrorState error={query.error} action={<Button variant="secondary" onClick={() => void query.refetch()}>{t("common.retry")}</Button>} /></div> : null}
        <div className="grid shrink-0 gap-6 p-4 sm:p-6 md:min-h-0 md:flex-1 md:grid-cols-[240px_minmax(0,1fr)] md:grid-rows-[minmax(0,1fr)]">
          <aside className="min-w-0 space-y-5 border-b border-platforma-border pb-5 md:min-h-0 md:overflow-y-auto md:border-b-0 md:border-r md:pb-0 md:pr-6">
            <div><h2 className="break-words text-2xl font-semibold leading-tight">{client.full_name}</h2>

            {client.is_archived || client.is_vip || client.has_no_reply ? <div className="mt-2 flex flex-wrap gap-2 text-xs text-platforma-subtle">{client.is_archived ? <span>{t("clients.card.archived")}</span> : null}{client.is_vip ? <span className="rounded-control bg-brand-50 px-2 py-1 text-brand-700">VIP</span> : null}{client.has_no_reply ? <span>{t("conversations.noReply")}</span> : null}</div> : null}</div>
            <section><h3 className="mb-3 font-semibold">{t("clients.contacts")}</h3><div className="space-y-3 text-sm">
              {client.email ? <a href={`mailto:${client.email}`} className="platforma-focus-ring flex items-start gap-2 rounded-control"><Mail size={17} className="shrink-0" /><span className="break-all">{client.email}</span></a> : null}
              {client.phone ? <a href={`tel:${client.phone}`} className="platforma-focus-ring flex items-start gap-2 rounded-control"><Phone size={17} className="shrink-0" /><span className="break-all">{client.phone}</span></a> : null}
              {!client.phone && !client.email ? <p className="text-platforma-subtle">{t("crmCard.noContacts")}</p> : null}
            </div></section>
            <Button variant="secondary" className="md:hidden" aria-expanded={detailsOpen} aria-controls={`${id}-summary`} onClick={() => setDetailsOpen(value => !value)}>{t("clients.details")}</Button>
            <div id={`${id}-summary`} className={`${detailsOpen ? "block" : "hidden"} space-y-5 md:block`}>
            <section className="border-t border-platforma-border pt-5"><h3 className="mb-3 font-semibold">{t("clients.card.responsible")}</h3><p className="flex items-start gap-2 text-sm"><UserRound size={17} className="shrink-0" /><span className="break-words">{client.manager_name || t("taskWorkspace.unassigned")}</span></p></section>
            <section className="border-t border-platforma-border pt-5"><h3 className="mb-3 font-semibold">{t("clients.notes")}</h3><p className="whitespace-pre-wrap break-words text-sm leading-6">{client.notes || t("crmCard.noNotesText")}</p></section>
            {data?.tags.length ? <section className="border-t border-platforma-border pt-5"><h3 className="mb-3 font-semibold">{t("clients.tags")}</h3><div className="flex flex-wrap gap-2">{data.tags.map(tag => <span key={tag.id} className="rounded-control bg-surface-muted px-2 py-1 text-xs">{tag.tag_name}</span>)}</div></section> : null}
            <PaymentsButton client={client} />
            </div>
          </aside>
          <div className="min-w-0 md:flex md:min-h-0 md:flex-col">
            <EntityCardTabs id={id} tabs={visibleTabs} active={tab} labels={labels} onChange={changeTab} />
            <div key={tab} role="tabpanel" id={`${id}-panel`} aria-label={t(labels[tab])} tabIndex={0} className="platforma-focus-ring rounded-control md:min-h-0 md:flex-1 md:overflow-y-auto md:[scrollbar-gutter:stable]" data-testid="crm-entity-drawer-content">
              {limited ? <p className="mb-4 text-sm text-platforma-subtle">{t("clients.card.limited")} <Link className="platforma-focus-ring rounded text-brand-700 underline" to={tab === "appointments" ? `/app/appointments?client=${client.id}` : `/app/clients/${client.id}`}>{t("clients.card.openPage")}</Link></p> : null}
              <div key={`${tab}:${revision}`}>{panel}</div>
              {tab === "appointments" && counts ? <p className="mt-4 text-xs text-platforma-subtle">{t("crmCard.timelineVisibleCount", { visible: data?.appointments.length || 0, total: counts.appointments })}</p> : null}
            </div>
          </div>
        </div>
      </>}
    </Dialog>
  </>;
}

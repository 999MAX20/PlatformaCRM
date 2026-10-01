import type { LucideIcon } from "lucide-react";
import { Archive, BriefcaseBusiness, CalendarCheck, ChevronDown, ClipboardList, Edit3, Inbox, Mail, MessageCircle, Phone, Plus, Sparkles, X } from "lucide-react";
import { useState } from "react";

import { Button } from "../../../components/ui/Button";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import { formatDate, formatDateTime } from "../../../lib/format";
import type { ClientTableRow, Translate } from "../types";
import { money, priorityLabel, sourceLabel } from "../utils";
import { ClientAvatar, ClientStatusBadge, TagPill } from "./ClientPrimitives";

function DetailSection({ title, icon: Icon, action, children }: { title: string; icon?: LucideIcon; action?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="border-t border-platforma-border px-4 py-1.5">
      <div className="mb-1.5 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm font-bold text-platforma-text">
          {Icon ? <Icon size={16} className="text-platforma-faint" /> : null}
          {title}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

function EmptyState({ text, action }: { text: string; action?: React.ReactNode }) {
  return (
    <div className="rounded-lg bg-surface-muted px-3 py-2.5 text-center">
      <p className="text-sm font-medium text-platforma-faint">{text}</p>
      {action ? <div className="mt-3">{action}</div> : null}
    </div>
  );
}

function MutedEmpty({ text }: { text: string }) {
  return <p className="text-sm font-medium text-platforma-faint">{text}</p>;
}

function ContactLine({ icon: Icon, children, action }: { icon: LucideIcon; children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="flex min-h-6 items-center justify-between gap-3 text-sm">
      <div className="flex min-w-0 items-center gap-2 text-platforma-subtle">
        <Icon size={15} className="shrink-0 text-platforma-faint" />
        <span className="truncate">{children}</span>
      </div>
      {action}
    </div>
  );
}

function TimelineRow({
  icon: Icon,
  title,
  meta,
  badge,
}: {
  icon: LucideIcon;
  title: string;
  meta: string;
  badge?: React.ReactNode;
}) {
  return (
    <div className="grid grid-cols-[68px_minmax(0,1fr)] gap-2 text-sm">
      <p className="text-xs font-medium text-platforma-faint">{meta}</p>
      <div className="flex min-w-0 items-center gap-2 text-platforma-subtle">
        <Icon size={15} className="shrink-0 text-platforma-faint" />
        <span className="min-w-0 truncate font-medium">{title}</span>
        {badge}
      </div>
    </div>
  );
}

function DealsTab({ row, t }: { row: ClientTableRow; t: Translate }) {
  if (!row.deals.length) return <div className="p-4"><EmptyState text={t("clients.noDeals")} /></div>;
  return (
    <div className="space-y-2 p-4">
      {row.deals.map((deal) => (
        <div key={deal.id} className="rounded-lg border border-platforma-border bg-white p-3">
          <div className="flex items-start justify-between gap-3">
            <p className="min-w-0 truncate text-sm font-bold text-platforma-text">{deal.title}</p>
            <StatusBadge status={deal.status} />
          </div>
          <div className="mt-2 flex items-center justify-between gap-3 text-xs font-semibold text-platforma-faint">
            <span>{money(deal.amount, deal.currency)}</span>
            <span>{formatDate(deal.updated_at)}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function TasksTab({ row, t }: { row: ClientTableRow; t: Translate }) {
  if (!row.tasks.length) return <div className="p-4"><EmptyState text={t("clients.noActiveTasks")} /></div>;
  return (
    <div className="space-y-2 p-4">
      {row.tasks.map((task) => (
        <div key={task.id} className="rounded-lg border border-platforma-border bg-white p-3">
          <div className="flex items-start justify-between gap-3">
            <p className="min-w-0 text-sm font-bold text-platforma-text">{task.title}</p>
            {priorityLabel(task.priority, t) ? <TagPill className="bg-[var(--platforma-info-soft)] text-platforma-info">{priorityLabel(task.priority, t)}</TagPill> : null}
          </div>
          <p className="mt-2 text-xs font-semibold text-platforma-faint">{task.due_at ? formatDateTime(task.due_at) : t("tasks.dueNone")}</p>
        </div>
      ))}
    </div>
  );
}

function FilesTab({ t }: { t: Translate }) {
  return <div className="p-4"><EmptyState text={t("clients.noFiles")} /></div>;
}

export function ClientInspector({
  row,
  onClose,
  onEdit,
  onFullCard,
  onOpenOverview,
  onOpenDeals,
  onOpenTasks,
  onOpenFiles,
  activeTab,
  onAddTag,
  onArchive,
  t,
}: {
  row: ClientTableRow | null;
  onClose: () => void;
  onEdit: () => void;
  onFullCard: () => void;
  onOpenOverview: () => void;
  onOpenDeals: () => void;
  onOpenTasks: () => void;
  onOpenFiles: () => void;
  activeTab: "overview" | "deals" | "tasks" | "files";
  onAddTag: () => void;
  onArchive: () => void;
  t: Translate;
}) {
  const [favoriteClientIds, setFavoriteClientIds] = useState<Set<number>>(() => new Set());

  if (!row) {
    return (
      <div className="min-h-[640px] bg-white xl:min-h-0 xl:h-full">
        <div className="grid h-full place-items-center p-8 text-center">
          <div>
            <ClientAvatar name="Client" size="lg" />
            <p className="mt-4 text-sm font-bold text-platforma-text">{t("clients.listHintTitle")}</p>
            <p className="mt-2 text-sm text-platforma-faint">{t("clients.listHintText")}</p>
          </div>
        </div>
      </div>
    );
  }

  const { client } = row;
  const isFavorite = favoriteClientIds.has(client.id);
  const latestDeal = row.deals[0];
  const latestLead = row.leads[0];
  const latestAppointment = row.appointments[0];
  const openDealValue = row.deals.filter((deal) => deal.status === "open").reduce((sum, deal) => sum + Number(deal.amount || 0), 0);
  const mainTask = row.tasks[0];
  const phoneDigits = client.phone?.replace(/\D/g, "") || "";
  const hasTelegram = Boolean(client.telegram_id || client.source === "telegram");
  const historyItems: Array<{ key: string; icon: LucideIcon; title: string; meta: string; badge?: React.ReactNode }> = [
    ...row.conversations.slice(0, 2).map((conversation) => ({
      key: `conversation-${conversation.id}`,
      icon: Phone,
      title: conversation.last_message?.direction === "outbound" ? t("clients.outboundContact") : t("clients.inboundContact"),
      meta: formatDateTime(conversation.last_message_at || conversation.updated_at),
    })),
    ...row.leads.slice(0, 2).map((lead) => ({
      key: `lead-${lead.id}`,
      icon: Inbox,
      title: t("clients.leadFallback", { id: lead.id }),
      meta: formatDateTime(lead.created_at),
      badge: <StatusBadge status={lead.status} />,
    })),
    ...row.appointments.slice(0, 2).map((appointment) => ({
      key: `appointment-${appointment.id}`,
      icon: CalendarCheck,
      title: t("clients.bookingFallback", { id: appointment.id }),
      meta: formatDateTime(appointment.start_at),
      badge: <StatusBadge status={appointment.status} />,
    })),
  ].slice(0, 4);
  const clientNextStepText = latestLead || latestAppointment
    ? t("clients.crmNextStepWithActivity")
    : t("clients.crmNextStepNeedsContact");

  function toggleFavorite() {
    setFavoriteClientIds((current) => {
      const next = new Set(current);
      if (next.has(client.id)) next.delete(client.id);
      else next.add(client.id);
      return next;
    });
  }

  return (
    <div className="min-h-0 bg-white xl:h-full xl:overflow-y-auto">
    <div className="sticky top-0 z-10 border-b border-platforma-border bg-white px-4 py-1.5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
            <ClientAvatar name={client.full_name} size="md" />
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h2 className="truncate text-sm font-bold text-platforma-text">{client.full_name}</h2>
                <button
                  type="button"
                  className={isFavorite ? "text-brand-700 transition hover:text-brand-800" : "text-platforma-faint transition hover:text-platforma-subtle"}
                  aria-label={t("clients.favorite")}
                  aria-pressed={isFavorite}
                  onClick={toggleFavorite}
                >
                  <Sparkles size={14} />
                </button>
              </div>
              <div className="mt-1 flex flex-wrap items-center gap-1.5">
                <ClientStatusBadge status={row.status} t={t} />
                <span className="text-xs font-medium text-platforma-faint">{formatDate(client.created_at)}</span>
              </div>
            </div>
          </div>
          <button type="button" onClick={onClose} className="grid h-8 min-h-8 w-8 min-w-8 shrink-0 place-items-center rounded-lg border border-platforma-border text-platforma-faint transition hover:bg-surface-hover hover:text-platforma-text" aria-label={t("common.close")}>
            <X size={16} />
          </button>
        </div>

        <div role="tablist" aria-label={t("clients.card")} className="mt-1.5 grid grid-cols-4 gap-1 border-b border-platforma-border text-center text-xs font-semibold text-platforma-faint">
          {[
            { label: t("clients.tabOverview"), id: "overview", onClick: onOpenOverview },
            { label: t("clients.tabDeals", { count: row.deals.length }), id: "deals", onClick: onOpenDeals },
            { label: t("clients.tabTasks", { count: row.tasks.length }), id: "tasks", onClick: onOpenTasks },
            { label: t("clients.tabFiles"), id: "files", onClick: onOpenFiles },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={activeTab === tab.id}
              onClick={tab.onClick}
              aria-current={activeTab === tab.id ? "page" : undefined}
              className={
                activeTab === tab.id
                  ? "cursor-pointer border-b-2 border-platforma-info bg-[var(--platforma-info-soft)] px-1 pb-1.5 text-platforma-info transition"
                  : "cursor-pointer border-b-2 border-transparent px-1 pb-1.5 transition hover:bg-surface-hover hover:text-platforma-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1"
                }
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div className="mt-2 grid grid-cols-2 gap-2">
          <Button
            type="button"
            size="sm"
            className="h-8 min-h-8 rounded-lg px-2 text-xs"
            disabled={!phoneDigits}
            onClick={() => phoneDigits && window.open(`tel:${phoneDigits}`, "_blank", "noopener,noreferrer")}
          >
            <Phone size={14} />
            {t("clients.call")}
          </Button>
          <Button
            type="button"
            size="sm"
            variant="secondary"
            className="h-8 min-h-8 rounded-lg px-2 text-xs"
            disabled={!phoneDigits && !hasTelegram}
            onClick={() => {
              if (phoneDigits) window.open(`https://wa.me/${phoneDigits}`, "_blank", "noopener,noreferrer");
              else if (hasTelegram) onFullCard();
            }}
          >
            <MessageCircle size={14} />
            {phoneDigits ? t("clients.openWhatsapp") : t("clients.fullCard")}
          </Button>
        </div>
      </div>

      {activeTab === "deals" ? <DealsTab row={row} t={t} /> : null}
      {activeTab === "tasks" ? <TasksTab row={row} t={t} /> : null}
      {activeTab === "files" ? <FilesTab t={t} /> : null}
      {activeTab === "overview" ? (
        <>
      <DetailSection
        title={t("clients.contacts")}
        action={
          <div className="flex items-center gap-1">
            <button type="button" onClick={onEdit} className="grid h-7 min-h-7 w-7 min-w-7 place-items-center rounded-md text-platforma-faint transition hover:bg-surface-hover hover:text-platforma-text" aria-label={t("clients.edit")}>
              <Edit3 size={15} />
            </button>
            <button type="button" onClick={onArchive} className="grid h-7 min-h-7 w-7 min-w-7 place-items-center rounded-md text-platforma-warning transition hover:bg-[var(--platforma-warning-soft)]" aria-label={t("clients.archiveAction")}>
              <Archive size={15} />
            </button>
          </div>
        }
      >
        <div className="space-y-1.5">
          <ContactLine
            icon={Phone}
            action={
              client.phone ? (
                <button type="button" onClick={() => window.open(`https://wa.me/${client.phone.replace(/\D/g, "")}`, "_blank", "noopener,noreferrer")} className="grid h-6 min-h-6 w-6 min-w-6 place-items-center text-emerald-600 transition hover:text-emerald-700" aria-label="WhatsApp">
                  <MessageCircle size={15} />
                </button>
              ) : null
            }
          >
            {client.phone || t("clients.phoneMissing")}
          </ContactLine>
          <ContactLine icon={Mail}>{client.email || t("clients.emailMissing")}</ContactLine>
          {hasTelegram ? <ContactLine icon={MessageCircle}>{t("clients.telegramConnected")}</ContactLine> : null}
          <ContactLine icon={BriefcaseBusiness}>{sourceLabel(client.source, t)}</ContactLine>
        </div>
      </DetailSection>

      <DetailSection title={t("clients.tags")} action={<button type="button" onClick={onAddTag} className="grid h-7 min-h-7 w-7 min-w-7 place-items-center text-platforma-faint transition hover:text-platforma-text" aria-label={t("clients.addTag")}><Plus size={15} /></button>}>
        {row.tags.length ? (
          <div className="flex flex-wrap gap-2">
            {row.tags.slice(0, 6).map((tag) => (
              <TagPill key={tag.id} className="bg-brand-50 text-brand-800">{tag.tag_name}</TagPill>
            ))}
          </div>
        ) : (
          <MutedEmpty text={t("clients.noTagsYet")} />
        )}
      </DetailSection>

      <DetailSection title={t("clients.latestDeal")} action={<ChevronDown size={16} className="text-platforma-faint" />}>
        {latestDeal ? (
          <div>
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-semibold text-platforma-text">{latestDeal.title}</p>
              <p className="text-sm font-semibold text-platforma-text">{money(latestDeal.amount, latestDeal.currency)}</p>
            </div>
            <div className="mt-1.5 h-1 rounded-full bg-surface-muted">
              <div className="h-1 rounded-full bg-platforma-info" style={{ width: `${Math.max(12, Math.min(100, latestDeal.probability || 35))}%` }} />
            </div>
            <div className="mt-1.5 flex justify-between text-xs font-medium text-platforma-faint">
              <span>{latestDeal.status === "open" ? t("deals.statusOpen") : latestDeal.status}</span>
              <span>{formatDate(latestDeal.updated_at)}</span>
            </div>
          </div>
        ) : (
          <MutedEmpty text={t("clients.noDealsOpenValue", { value: money(openDealValue) })} />
        )}
      </DetailSection>

      <DetailSection title={t("clients.nextTask")} icon={ClipboardList}>
        {mainTask ? (
          <div className="rounded-lg bg-surface-muted px-2.5 py-2">
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-platforma-text">{mainTask.title}</p>
                <p className="mt-0.5 text-xs font-medium text-platforma-faint">{mainTask.due_at ? formatDateTime(mainTask.due_at) : t("tasks.dueNone")}</p>
              </div>
              {priorityLabel(mainTask.priority, t) ? <TagPill className="bg-[var(--platforma-info-soft)] text-platforma-info">{priorityLabel(mainTask.priority, t)}</TagPill> : null}
            </div>
          </div>
        ) : (
          <MutedEmpty text={t("clients.noActiveTasks")} />
        )}
      </DetailSection>

      <DetailSection title={t("clients.history")} action={<button type="button" onClick={onFullCard} className="text-xs font-semibold text-platforma-info transition hover:text-platforma-info">{t("clients.viewAll")}</button>}>
        <div className="space-y-2">
          {historyItems.map((item) => (
            <TimelineRow key={item.key} icon={item.icon} title={item.title} meta={item.meta} badge={item.badge} />
          ))}
          {!historyItems.length ? <EmptyState text={t("clients.emptyHistory")} /> : null}
        </div>
      </DetailSection>

      <div className="px-4 pb-3">
        <div className="rounded-xl border border-platforma-border bg-surface-muted p-2">
          <div className="flex items-start gap-2.5">
            <ClipboardList size={15} className="mt-0.5 shrink-0 text-platforma-subtle" />
            <div className="min-w-0">
              <p className="text-sm font-bold text-platforma-text">{t("clients.crmNextStepTitle")}</p>
              <p className="mt-0.5 text-xs leading-4 text-platforma-subtle">
                {clientNextStepText}
              </p>
              <Button type="button" size="sm" variant="secondary" className="mt-1 h-7 min-h-7 px-2.5 text-xs" onClick={onFullCard}>
                {t("clients.crmNextStepAction")}
              </Button>
            </div>
          </div>
        </div>
      </div>
        </>
      ) : null}
    </div>
  );
}

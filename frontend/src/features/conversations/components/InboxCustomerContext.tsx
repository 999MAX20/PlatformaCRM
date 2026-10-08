import { ArrowUpRight, BriefcaseBusiness, CalendarDays, CalendarPlus, CheckSquare, Inbox, Link2, UserRound, X } from "lucide-react";

import type { InboxContext } from "../../../api/inbox";
import { ActionMenu, type ActionMenuItem } from "../../../components/ui/ActionMenu";
import { Button } from "../../../components/ui/Button";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import { useI18n } from "../../../lib/i18n";

type Props = {
  data?: InboxContext;
  loading: boolean;
  error: unknown;
  retrying: boolean;
  menuItems: ActionMenuItem[];
  inDrawer?: boolean;
  onRetry: () => void;
  onClose: () => void;
  onNavigate: (href: string) => void;
  onLinkClient: () => void;
  onAddLink: () => void;
};

export function InboxCustomerContext({ data, loading, error, retrying, menuItems, inDrawer, onRetry, onClose, onNavigate, onLinkClient, onAddLink }: Props) {
  const { t, language } = useI18n();
  const client = data?.client.data;
  const appointments = data?.appointments;
  const deal = data?.deal.data;
  const lead = data?.lead.data;
  const task = data?.task;
  const linkClass = "platforma-focus-ring flex min-h-11 w-full items-center justify-between gap-2 rounded-control text-left text-sm font-semibold text-platforma-text hover:text-brand-700 hover:underline underline-offset-4 lg:min-h-9 [overflow-wrap:anywhere]";
  const sectionClass = "border-t border-platforma-border py-3";
  const headingClass = "mb-1 flex items-center gap-2 text-xs font-bold text-platforma-muted";
  function entityLink(href: string, label: string) {
    return <a href={href} className={linkClass} onClick={event => {
      if (event.button || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault(); onNavigate(href);
    }}><span>{label}</span><ArrowUpRight aria-hidden="true" size={14} className="shrink-0 text-brand-600" /></a>;
  }
  function dateLabel(value: string, timeOnly = false) {
    return new Intl.DateTimeFormat(language, {
      ...(timeOnly ? {} : { day: "numeric" as const, month: "short" as const, year: "numeric" as const }),
      hour: "2-digit", minute: "2-digit", timeZone: data?.timezone || "UTC",
    }).format(new Date(value));
  }
  function unavailable(section: string) {
    return <p className="text-xs text-platforma-muted" data-testid={`inbox-context-${section}-forbidden`}>{t(`conversations.contextDenied.${section}`)}</p>;
  }
  const canAdd = data && (["lead", "deal"] as const).some(kind => data[kind].state === "empty" && (data.actions[`link_${kind}`] || data.actions[`create_${kind}`]));
  return <div className="flex min-h-0 flex-1 flex-col bg-surface-card" data-testid="inbox-customer-context">
    <header className="flex min-h-14 shrink-0 items-center gap-2 border-b border-platforma-border px-4">
      <h2 className="min-w-0 flex-1 text-base font-bold text-platforma-text">{t("conversations.aboutClient")}</h2>
      {menuItems.length ? <ActionMenu label={t("conversations.contextActions")} items={menuItems} overlay={inDrawer ? "drawer" : undefined} /> : null}
      <Button variant="icon" size="icon" onClick={onClose} aria-label={t("conversations.closeContext")}><X size={18} /></Button>
    </header>
    <div className="min-h-0 flex-1 overflow-y-auto px-4" aria-busy={loading}>
      {loading ? <div className="py-5"><LoadingState /></div> : error ? <div className="py-5"><ErrorState error={error} message={t("conversations.contextLoadError")} action={<Button variant="secondary" size="sm" onClick={onRetry} isLoading={retrying}>{t("common.retry")}</Button>} /></div> : data ? <>
        <section className="py-3" aria-label={t("common.client")}>
          {client ? <>
            <div className="flex items-start gap-3">
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-brand-50 text-brand-700"><UserRound size={20} aria-hidden="true" /></span>
              <div className="min-w-0 flex-1">
                {entityLink(client.href, client.name || t("conversations.clientFallback", { id: client.id }))}
                {client.phone ? <p className="break-words text-sm text-platforma-muted">{client.phone}</p> : null}
                {client.email ? <p className="text-sm text-platforma-muted [overflow-wrap:anywhere]">{client.email}</p> : null}
                {!client.phone && !client.email ? <p className="text-xs text-platforma-muted">{t("conversations.noContact")}</p> : null}
              </div>
            </div>
            {client.notes ? <p className="mt-3 line-clamp-3 whitespace-pre-wrap border-l-2 border-platforma-border pl-3 text-xs leading-5 text-platforma-muted [overflow-wrap:anywhere]">{client.notes}</p> : null}
          </> : data.client.state === "forbidden" ? unavailable("client") : data.actions.link_client || data.actions.create_client ?
            <Button variant="secondary" size="sm" onClick={onLinkClient}><Link2 size={16} />{t("conversations.linkClientAction")}</Button> : null}
        </section>
        {appointments?.state === "forbidden" ? <section className={sectionClass}>{unavailable("appointments")}</section> : appointments?.items.length ? <section className={sectionClass} aria-label={t("calendar.title")}>
          <h3 className={headingClass}><CalendarDays size={16} aria-hidden="true" className="shrink-0" />{t(appointments.kind === "conversation" ? "conversations.contextAppointments" : "conversations.clientUpcomingAppointments")}</h3>
          <div className="divide-y divide-platforma-border">{appointments.items.map(appointment => <div key={appointment.id} className="py-2 first:pt-0 last:pb-0">
            {entityLink(appointment.href, `${dateLabel(appointment.start_at)} – ${dateLabel(appointment.end_at, true)}`)}
            {appointment.service_name ? <p className="text-sm text-platforma-text [overflow-wrap:anywhere]">{appointment.service_name}</p> : null}
            {appointment.resource_name ? <p className="mt-1 text-xs text-platforma-muted [overflow-wrap:anywhere]">{appointment.resource_name}</p> : null}
            <StatusBadge status={appointment.status} size="sm" className="mt-2" />
          </div>)}</div>
          {appointments.has_more && client ? <div className="mt-2">{entityLink(client.href, t("conversations.moreClientAppointments"))}</div> : null}
        </section> : null}
        {data.actions.book && client ? <section className="border-t border-platforma-border py-4"><Button variant="secondary" size="sm" onClick={() => onNavigate(`/app/calendar?create=1&client=${client.id}`)}><CalendarPlus size={16} />{t("conversations.bookClient")}</Button></section> : null}
        {deal || lead || task || data.deal.state === "forbidden" || data.lead.state === "forbidden" ? <section aria-label={t("conversations.relatedWork")}>
          {deal ? <section className={sectionClass} aria-label={t("conversations.linkedDeal")}><h3 className={headingClass}><BriefcaseBusiness size={16} aria-hidden="true" />{t("conversations.linkedDeal")}</h3>
            {entityLink(deal.href, deal.title || t("conversations.dealFallback", { id: deal.id }))}
            {deal.stage_name ? <p className="text-xs text-platforma-muted [overflow-wrap:anywhere]">{deal.stage_name}</p> : <StatusBadge status={deal.status} size="sm" />}
            {deal.amount !== null && deal.currency ? <p className="mt-1 text-sm font-semibold tabular-nums text-platforma-text">{new Intl.NumberFormat(language, { style: "currency", currency: deal.currency, maximumFractionDigits: 2 }).format(Number(deal.amount))}</p> : null}
          </section> : data.deal.state === "forbidden" ? <div className={sectionClass}>{unavailable("deal")}</div> : null}
          {lead ? <section className={sectionClass} aria-label={t("conversations.linkedLead")}><h3 className={headingClass}><Inbox size={16} aria-hidden="true" />{t("conversations.linkedLead")}</h3>
            {entityLink(lead.href, lead.title || t("conversations.leadFallback", { id: lead.id }))}<div><StatusBadge status={lead.status} size="sm" /></div>
          </section> : data.lead.state === "forbidden" ? <div className={sectionClass}>{unavailable("lead")}</div> : null}
          {task ? <section className={sectionClass} aria-label={t("conversations.nextTask")}><h3 className={headingClass}><CheckSquare size={16} aria-hidden="true" />{t("conversations.nextTask")}</h3>{entityLink(task.href, task.title)}{task.due_at ? <p className="text-xs tabular-nums text-platforma-muted">{dateLabel(task.due_at)}</p> : null}</section> : null}
        </section> : null}
        {canAdd ? <div className="border-t border-platforma-border py-4"><Button variant="ghost" size="sm" onClick={onAddLink}><Link2 size={16} />{t("conversations.addLink")}</Button></div> : null}
      </> : null}
    </div>
  </div>;
}

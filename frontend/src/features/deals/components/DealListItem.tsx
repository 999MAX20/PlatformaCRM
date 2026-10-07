import { memo } from "react";
import { CalendarClock, MoreHorizontal } from "lucide-react";

import { cn } from "../../../lib/cn";
import { formatDateTime } from "../../../lib/format";
import type { DealRow, Translate } from "../types";
import { DealAmount } from "./common/DealAmount";

export const DealListItem = memo(function DealListItem({ deal, selected, onSelect, onOpen, onMore, t }: {
  deal: DealRow;
  selected: boolean;
  onSelect: (deal: DealRow) => void;
  onOpen: (deal: DealRow) => void;
  onMore: (deal: DealRow) => void;
  t: Translate;
}) {
  const owner = deal.ownerEntity?.user.full_name || deal.ownerEntity?.user.email || "";
  const initials = owner.split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
  const dueAt = deal.nextTask?.due_at || deal.next_action_at;
  const overdue = deal.status === "open" && Boolean(dueAt && new Date(dueAt).getTime() < Date.now());
  const nextTitle = deal.nextTask?.title || t(deal.next_action_at ? "deals.nextAction" : "deals.noTasksFilter");
  return (
    <article draggable onDragStart={(event) => event.dataTransfer.setData("text/plain", String(deal.id))}
      className={cn("group relative rounded-control border border-platforma-border bg-surface-card p-2.5 transition hover:border-brand-200 hover:shadow-soft", selected && "border-brand-100 bg-brand-50 ring-2 ring-[var(--platforma-focus-ring)]")}>
      <button type="button" className="platforma-focus-ring block w-full min-w-0 rounded-control text-left" onClick={() => onSelect(deal)} onDoubleClick={() => onOpen(deal)}>
        <h3 className="line-clamp-2 pr-6 text-sm font-semibold leading-5 text-platforma-text" title={deal.title}>{deal.title}</h3>
        <div className="mt-0.5 flex items-center justify-between gap-2">
          <div className="min-w-0">
            <p className="truncate text-xs leading-4 text-platforma-muted">{deal.clientEntity?.full_name || t("deals.clientMissing")}</p>
            <DealAmount value={deal.amount} currency={deal.currency} className="block text-sm font-medium leading-5 text-platforma-text" />
          </div>
          {owner ? <span title={owner} aria-label={owner} className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-surface-muted text-xs font-medium text-platforma-subtle">{initials}</span> : null}
        </div>
        <div className={cn("mt-2 flex min-w-0 flex-wrap items-center gap-x-1.5 gap-y-1 border-t border-platforma-border pt-2 text-xs leading-4", overdue ? "text-platforma-danger" : "text-platforma-muted")} title={nextTitle}>
          <CalendarClock size={14} className="shrink-0" />
          <span className="min-w-0 flex-1 truncate">{nextTitle}</span>
          {dueAt ? <span className="w-full pl-5 tabular-nums">{formatDateTime(dueAt)}</span> : null}
        </div>
      </button>
      <button type="button" data-testid="deal-card-action-open" className="platforma-focus-ring absolute right-1.5 top-1.5 grid h-6 w-6 place-items-center rounded-control text-platforma-muted hover:bg-brand-50 hover:text-platforma-text"
        onClick={(event) => { event.stopPropagation(); onMore(deal); }} onDoubleClick={(event) => event.stopPropagation()} aria-label={t("deals.openDealContext", { title: deal.title })}>
        <MoreHorizontal size={16} />
      </button>
    </article>
  );
});

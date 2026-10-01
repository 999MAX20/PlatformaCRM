import {
  CheckCheck,
  MoreHorizontal,
} from "lucide-react";

import {
  CRM_TABLE_CHECKBOX_COLUMN,
  CRM_TABLE_MIN_WIDTH,
  CRM_TABLE_ROW_GRID_CLASS,
  CRM_TABLE_WIDE_MIN_WIDTH,
} from "../../../components/crm";
import { useAuth } from "../../auth/AuthProvider";
import { hasPermission } from "../../../lib/permissions";
import { cn } from "../../../lib/cn";
import { formatDateTime } from "../../../lib/format";
import type { Client, Id, Lead, Service } from "../../../types";
import {
  leadColumnWidths,
  statusClass,
  type LeadAiInsight,
  type LeadColumnKey,
  type Translate,
} from "../types";
import {
  formatRelativeTime,
  getClient,
  getService,
  getSourceLabel,
  getStatusLabel,
  initials,
  leadAiInsight,
  nextAction,
  TruncatedText,
} from "../utils/leadFormat";
import { SourceBadge } from "./common/SourceBadge";

function ManagerAvatar({ name }: { name?: string }) {
  if (!name)
    return <span className="text-xs font-bold text-platforma-muted">-</span>;
  return (
    <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-surface-muted text-[11px] font-bold text-brand-700 ring-1 ring-surface-card">
      {initials(name)}
    </span>
  );
}

function LeadTableRow({
  lead,
  client,
  service,
  responsibleName,
  aiInsight,
  teamList,
  selected,
  bulkSelected,
  visibleColumns,
  columnOrder,
  onClick,
  onToggleBulk,
  onAssign,
  onContextMenu,
  t,
}: {
  lead: Lead;
  client?: Client;
  service?: Service;
  responsibleName?: string;
  aiInsight: LeadAiInsight;
  teamList: Array<{ user: { id: Id; full_name?: string; email: string } }>;
  selected: boolean;
  bulkSelected: boolean;
  visibleColumns: Record<LeadColumnKey, boolean>;
  columnOrder: LeadColumnKey[];
  onClick: () => void;
  onToggleBulk: () => void;
  onAssign: (userId?: Id) => void;
  onContextMenu: (event: React.MouseEvent) => void;
  t: Translate;
}) {
  const { user } = useAuth();
  const canAssign = hasPermission(user, lead.business, "leads", "update") && teamList.length > 0;
  const title = client?.full_name || t("leads.leadFallback", { id: lead.id });
  const isHot = lead.status === "new" && !lead.responsible_user;
  const activeColumns = columnOrder.filter((column) => visibleColumns[column]);
  const needsWideTable = activeColumns.length > 5;
  const gridTemplateColumns = `${CRM_TABLE_CHECKBOX_COLUMN} ${activeColumns.map((column) => leadColumnWidths[column]).join(" ")} 56px`;
  const cells: Record<LeadColumnKey, React.ReactNode> = {
    lead: (
      <button
        type="button"
        data-testid="lead-row-keyboard-open"
        className="platforma-focus-ring -m-1 flex min-w-0 items-center gap-3 rounded-control p-1 text-left"
        aria-label={t("leads.openContext", { title })}
        onClick={(event) => {
          event.stopPropagation();
          onClick();
        }}
      >
        <span className="grid h-9 w-9 shrink-0 place-items-center overflow-hidden rounded-full bg-surface-muted text-xs font-bold text-brand-700">
          {initials(title)}
        </span>
        <span className="min-w-0">
          <TruncatedText className="font-bold text-platforma-text">
            {title}
          </TruncatedText>
          <TruncatedText className="text-xs font-semibold text-platforma-muted">
            {service?.name || lead.message || getSourceLabel(lead.source, t)}
          </TruncatedText>
        </span>
      </button>
    ),
    phone: (
      <span className="truncate font-semibold text-platforma-text">
        {client?.phone || t("leads.noPhoneLower")}
      </span>
    ),
    source: (
      <span className="flex min-w-0">
        <SourceBadge source={lead.source} t={t} />
      </span>
    ),
    status: (
      <span
        className={cn(
          "inline-flex max-w-full items-center rounded-full px-2.5 py-1 text-xs font-bold ring-1",
          statusClass[lead.status],
        )}
      >
        {getStatusLabel(lead.status, t)}
      </span>
    ),
    priority: (
      <span className="flex items-center gap-2">
        <span
          className={cn(
            "h-2 w-2 rounded-full",
            isHot
              ? "bg-platforma-danger"
              : lead.status === "new"
                ? "bg-platforma-warning"
                : "bg-platforma-success",
          )}
        />
        <span className="text-xs font-bold text-platforma-muted">
          {isHot ? t("leads.priorityHot") : t("leads.priorityNormal")}
        </span>
      </span>
    ),
    manager: (
      <span
        className="flex min-w-0 items-center gap-2 pr-3"
        onClick={(event) => event.stopPropagation()}
      >
        <ManagerAvatar name={responsibleName} />
        {canAssign ? <select
          className="w-0 min-w-0 flex-1 truncate rounded-lg border border-transparent bg-transparent text-xs font-bold text-platforma-muted outline-none hover:border-platforma-border hover:bg-surface-card"
          value={lead.responsible_user ? String(lead.responsible_user) : ""}
          onChange={(event) =>
            onAssign(
              event.target.value ? Number(event.target.value) : undefined,
            )
          }
          aria-label={t("leads.responsible")}
        >
          <option value="">{t("leads.withoutManager")}</option>
          {teamList.map((member) => (
            <option key={member.user.id} value={member.user.id}>
              {member.user.full_name || member.user.email}
            </option>
          ))}
        </select> : <span className="min-w-0 truncate text-sm text-platforma-subtle" title={responsibleName}>{responsibleName || t("leads.withoutManager")}</span>}
      </span>
    ),
    activity: (
      <span className="truncate text-xs font-bold text-platforma-muted">
        {formatRelativeTime(lead.updated_at, t)}
      </span>
    ),
    next: (
      <span className="min-w-0">
        <TruncatedText className="font-bold text-platforma-text">
          {lead.next_task_title || nextAction(lead, t)}
        </TruncatedText>
        <span className="block truncate text-xs text-platforma-muted">
          {lead.next_task_due_at ? formatDateTime(lead.next_task_due_at) : null}
        </span>
      </span>
    ),
  };
  return (
    <div
      data-testid="lead-row-open"
      className={cn(
        CRM_TABLE_ROW_GRID_CLASS,
        selected && "bg-brand-50/70 shadow-[inset_3px_0_0_var(--platforma-brand)]",
        bulkSelected && "bg-surface-muted",
        aiInsight.stale && !selected && "bg-[var(--platforma-warning-soft)]/45",
      )}
      style={{
        gridTemplateColumns,
        minWidth: needsWideTable
          ? CRM_TABLE_WIDE_MIN_WIDTH
          : CRM_TABLE_MIN_WIDTH,
      }}
      onClick={onClick}
      onContextMenu={onContextMenu}
    >
      <label
        className="flex h-8 w-8 items-center justify-center"
        onClick={(event) => event.stopPropagation()}
      >
        <input
          className="peer sr-only"
          type="checkbox"
          checked={bulkSelected}
          onChange={onToggleBulk}
          aria-label={t("leads.selectLeadRowContext", { title })}
        />
        <span
          className={cn(
            "grid h-5 w-5 place-items-center rounded border peer-focus-visible:ring-2 peer-focus-visible:ring-brand-500",
            bulkSelected
              ? "border-brand-500 bg-brand-500 text-platforma-ink"
              : "border-platforma-border bg-surface-card",
          )}
        >
          {bulkSelected ? <CheckCheck size={13} /> : null}
        </span>
      </label>
      {activeColumns.map((column) => (
        <span key={column} className="min-w-0">
          {cells[column]}
        </span>
      ))}
      <span
        className="flex items-center justify-end gap-2"
        onClick={(event) => event.stopPropagation()}
      >
        {[
          {
            id: "more",
            label: t("leads.moreActionsContext", { title }),
            icon: MoreHorizontal,
            onClick: (event: React.MouseEvent) => onContextMenu(event),
          },
        ].map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              type="button"
              data-testid={`lead-row-action-${item.id}`}
              className="grid h-8 w-8 place-items-center rounded-control border border-platforma-border bg-surface-card text-platforma-muted shadow-sm transition hover:border-brand-100 hover:bg-brand-50 hover:text-brand-700"
              aria-label={item.label}
              title={item.label}
              onClick={(event) => {
                event.stopPropagation();
                item.onClick(event);
              }}
            >
              <Icon size={15} />
            </button>
          );
        })}
      </span>
    </div>
  );
}

export function VirtualizedLeadTableRows({
  rows,
  selected,
  selectedLeadIds,
  clientList,
  serviceList,
  teamList,
  aiInsights,
  allLeads,
  visibleColumns,
  columnOrder,
  selectLead,
  toggleBulkLead,
  assignLead,
  openContextMenu,
  t,
}: {
  rows: Lead[];
  selected: Lead | null;
  selectedLeadIds: Id[];
  clientList: Client[];
  serviceList: Service[];
  teamList: Array<{ user: { id: Id; full_name?: string; email: string } }>;
  aiInsights: Map<Id, LeadAiInsight>;
  allLeads: Lead[];
  visibleColumns: Record<LeadColumnKey, boolean>;
  columnOrder: LeadColumnKey[];
  selectLead: (lead: Lead) => void;
  toggleBulkLead: (id: Id) => void;
  assignLead: (lead: Lead, userId?: Id) => void;
  openContextMenu: (event: React.MouseEvent, lead: Lead) => void;
  t: Translate;
}) {
  const activeColumns = columnOrder.filter((column) => visibleColumns[column]);
  const needsWideTable = activeColumns.length > 5;
  const gridTemplateColumns = `${CRM_TABLE_CHECKBOX_COLUMN} ${activeColumns.map((column) => leadColumnWidths[column]).join(" ")} 56px`;

  return (
    <div className="hidden lg:block">
      <div
        className="min-w-0"
        style={{
          minWidth: needsWideTable ? CRM_TABLE_WIDE_MIN_WIDTH : undefined,
        }}
      >
        {rows.map((lead, index) => {
          const responsible = teamList.find(
            (member) => member.user.id === lead.responsible_user,
          );
          return (
            <div key={lead.id} data-index={index}>
              <LeadTableRow
                lead={lead}
                client={getClient(lead, clientList)}
                service={getService(lead, serviceList)}
                responsibleName={
                  lead.responsible_name || lead.responsible_email || responsible?.user.full_name || responsible?.user.email
                }
                aiInsight={
                  aiInsights.get(lead.id) ||
                  leadAiInsight(lead, clientList, serviceList, allLeads, t)
                }
                teamList={teamList}
                selected={lead.id === selected?.id}
                bulkSelected={selectedLeadIds.includes(lead.id)}
                visibleColumns={visibleColumns}
                columnOrder={columnOrder}
                onClick={() => selectLead(lead)}
                onToggleBulk={() => toggleBulkLead(lead.id)}
                onAssign={(userId) => assignLead(lead, userId)}
                onContextMenu={(event) => openContextMenu(event, lead)}
                t={t}
              />
            </div>
          );
        })}
        {!rows.length ? null : (
          <div
            className="grid h-0"
            style={{
              gridTemplateColumns,
              minWidth: needsWideTable
                ? CRM_TABLE_WIDE_MIN_WIDTH
                : CRM_TABLE_MIN_WIDTH,
            }}
            aria-hidden="true"
          />
        )}
      </div>
    </div>
  );
}

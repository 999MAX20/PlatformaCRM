import type { ReactNode } from "react";
import { ArrowRight, Inbox } from "lucide-react";
import type { InboxConversation, InboxFilters } from "../../../api/inbox";
import type { InboxSummary } from "../../../api/inbox";
import { Link } from "react-router";
import { WorkQueueListPane } from "../../../components/layout/WorkQueueLayout";
import { Button } from "../../../components/ui/Button";
import { LoadingState } from "../../../components/ui/StateViews";
import { StatusNotice } from "../../../components/ui/StatusNotice";
import type { InboxSort, Translate } from "../conversationTypes";
import { ConversationItem } from "./ConversationItem";
import { ConversationQueueFilters } from "./ConversationQueueFilters";

type FilterOption = { value: string; label: string };
type AgentFilterOption = { value: string | number; label: string };

type ConversationListPaneProps = {
  mobileThreadOpen: boolean;
  connectChannelAction?: ReactNode;
  filters: InboxFilters;
  sortBy: InboxSort;
  hasActiveFilters: boolean;
  activeFilterSummary: string[];
  queueFilterOptions: FilterOption[];
  ownerFilterOptions: FilterOption[];
  agentFilterOptions: AgentFilterOption[];
  channelOptions: FilterOption[];
  priorityOptions: FilterOption[];
  statusOptions: FilterOption[];
  sortOptions: FilterOption[];
  onQueueChange: (value: string) => void;
  onOwnerChange: (value: string) => void;
  onFilterChange: (filters: InboxFilters) => void;
  onSortChange: (value: string) => void;
  onReset: () => void;
  items: InboxConversation[];
  sortedItems: InboxConversation[];
  selectedId?: number | null;
  loading: boolean;
  bulkMode: boolean;
  selectedIds: number[];
  onSelectVisible: () => void;
  onResetBulk: () => void;
  onBulkAction: (action: "markRead" | "assign" | "handoff" | "pauseBot" | "close") => void;
  bulkPending: boolean;
  onToggleBulkId: (id: number) => void;
  onSelectConversation: (id: number) => void;
  priorityActions: InboxSummary["next_actions"];
  unavailableChannelCount: number;
  connectorReadinessLoading: boolean;
  connectorReadinessError: boolean;
  connectorReadinessRetrying: boolean;
  onRetryConnectorReadiness: () => void;
  canViewIntegrations: boolean;
  t: Translate;
};

export function ConversationListPane({
  mobileThreadOpen,
  connectChannelAction,
  filters,
  sortBy,
  hasActiveFilters,
  activeFilterSummary,
  queueFilterOptions,
  ownerFilterOptions,
  agentFilterOptions,
  channelOptions,
  priorityOptions,
  statusOptions,
  sortOptions,
  onQueueChange,
  onOwnerChange,
  onFilterChange,
  onSortChange,
  onReset,
  items,
  sortedItems,
  selectedId,
  loading,
  bulkMode,
  selectedIds,
  onSelectVisible,
  onResetBulk,
  onBulkAction,
  bulkPending,
  onToggleBulkId,
  onSelectConversation,
  priorityActions,
  unavailableChannelCount,
  connectorReadinessLoading,
  connectorReadinessError,
  connectorReadinessRetrying,
  onRetryConnectorReadiness,
  canViewIntegrations,
  t,
}: ConversationListPaneProps) {
  return (
    <WorkQueueListPane className="relative" mobileDetailOpen={mobileThreadOpen}>
      <ConversationQueueFilters
        filters={filters}
        sortBy={sortBy}
        hasActiveFilters={hasActiveFilters}
        activeFilterSummary={activeFilterSummary}
        queueOptions={queueFilterOptions}
        ownerOptions={ownerFilterOptions}
        agentOptions={agentFilterOptions}
        channelOptions={channelOptions}
        priorityOptions={priorityOptions}
        statusOptions={statusOptions}
        sortOptions={sortOptions}
        labels={{
          filters: t("conversations.filters"),
          advancedFilters: t("conversations.advancedFilters"),
          resetFilters: t("conversations.resetFilters"),
          agent: t("conversations.agent"),
          channel: t("conversations.channel"),
          priority: t("conversations.priority"),
          status: t("conversations.status"),
          bot: t("conversations.bot"),
          sort: t("conversations.sort"),
          noFilter: t("conversations.noFilter"),
          botEnabled: t("conversations.botActive"),
          botPaused: t("conversations.botPaused"),
        }}
        onQueueChange={onQueueChange}
        onOwnerChange={onOwnerChange}
        onFilterChange={onFilterChange}
        onSortChange={onSortChange}
        onReset={onReset}
      />

      {priorityActions.length ? (
        <div className="border-b border-platforma-border bg-surface-warm px-3 py-1" data-testid="inbox-priority-actions">
          {priorityActions.slice(0, 3).map((action) => (
            <Link
              key={`${action.href}-${action.label}`}
              to={action.href}
              className="platforma-focus-ring flex min-h-11 items-center justify-between gap-2 rounded-control px-1 text-xs font-semibold text-platforma-text transition hover:bg-brand-50 lg:min-h-8"
            >
              <span className="truncate">{action.code ? t(`conversations.nextAction.${action.code}`) : action.label}</span>
              <ArrowRight aria-hidden="true" size={14} className="shrink-0 text-brand-700" />
            </Link>
          ))}
        </div>
      ) : null}

      {connectorReadinessLoading ? (
        <div data-testid="inbox-provider-status-loading"><LoadingState /></div>
      ) : null}

      {connectorReadinessError ? (
        <StatusNotice
          compact
          className="rounded-none border-x-0 border-t-0 shadow-none"
          data-testid="inbox-provider-status-unavailable"
          tone="warning"
          role="status"
          title={t("conversations.channelStatusUnavailable")}
          action={<Button
            type="button"
            variant="secondary"
            size="sm"
            className="min-h-8 py-1 text-xs"
            data-testid="inbox-provider-status-retry"
            isLoading={connectorReadinessRetrying}
            onClick={onRetryConnectorReadiness}
          >
            {t("common.retry")}
          </Button>}
        />
      ) : null}

      {unavailableChannelCount ? (
        <StatusNotice
          compact
          className="rounded-none border-x-0 border-t-0 shadow-none"
          data-testid="inbox-provider-unavailable"
          tone="warning"
          title={t("conversations.channelsUnavailable", { count: unavailableChannelCount })}
          action={canViewIntegrations ? (
            <Link className="platforma-focus-ring inline-flex rounded-control px-2 py-1 font-bold text-platforma-warning underline" to="/app/ai-agents">
              {t("conversations.openIntegrations")}
            </Link>
          ) : null}
        />
      ) : null}

      {items.length ? (
        <div className="border-b border-platforma-border px-3 py-2">
          {!bulkMode ? (
            <button type="button" data-testid="conversation-select-multiple" className="platforma-focus-ring rounded-control text-xs font-bold text-brand-700" onClick={onSelectVisible}>
              {t("conversations.selectMultiple")}
            </button>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-bold text-platforma-text">{t("conversations.selectedCount", { count: selectedIds.length })}</p>
                <button type="button" className="text-sm font-bold text-platforma-muted transition hover:text-platforma-text" onClick={onResetBulk}>
                  {t("common.cancel")}
                </button>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button className="h-8 rounded-control px-3 text-xs" variant="secondary" disabled={!selectedIds.length} onClick={() => onBulkAction("markRead")} isLoading={bulkPending}>
                  {t("conversations.markRead")}
                </Button>
                <Button className="h-8 rounded-control px-3 text-xs" variant="secondary" disabled={!selectedIds.length} onClick={() => onBulkAction("assign")} isLoading={bulkPending}>
                  {t("conversations.take")}
                </Button>
                <Button className="h-8 rounded-control px-3 text-xs" variant="warning" disabled={!selectedIds.length} onClick={() => onBulkAction("pauseBot")} isLoading={bulkPending}>
                  {t("conversations.pause")}
                </Button>
                <Button className="h-8 rounded-control px-3 text-xs" variant="secondary" disabled={!selectedIds.length} onClick={() => onBulkAction("handoff")} isLoading={bulkPending}>
                  {t("conversations.operator")}
                </Button>
                <Button className="h-8 rounded-control px-3 text-xs" variant="secondary" disabled={!selectedIds.length} onClick={() => onBulkAction("close")} isLoading={bulkPending}>
                  {t("common.close")}
                </Button>
              </div>
            </div>
          )}
        </div>
      ) : null}

      <div className="min-h-0 flex-1 overflow-y-auto">
        {loading ? <div className="p-5"><LoadingState /></div> : null}
        {!loading && !items.length ? (
          <div className="pointer-events-none absolute inset-0 grid place-items-center px-5 text-center">
            <div className="relative w-full">
              <div className="absolute inset-x-0 bottom-full mb-3 flex justify-center text-platforma-subtle">
                <Inbox aria-hidden="true" size={22} />
              </div>
              <p className="text-base font-semibold text-platforma-ink">{t(hasActiveFilters ? "common.noResults" : "conversations.emptyTitle")}</p>
              <div className="absolute inset-x-0 top-full mt-2 text-sm leading-6 text-platforma-subtle">
                {hasActiveFilters ? <Button className="pointer-events-auto" variant="secondary" size="sm" onClick={onReset}>{t("conversations.resetFilters")}</Button> : <p>{t("conversations.emptyText")}</p>}
                {!hasActiveFilters && connectChannelAction ? <div className="pointer-events-auto mt-4 lg:hidden">{connectChannelAction}</div> : null}
              </div>
            </div>
          </div>
        ) : null}
        {sortedItems.map((conversation) => (
          <ConversationItem
            key={conversation.id}
            conversation={conversation}
            active={conversation.id === selectedId}
            selectable={bulkMode}
            selectedForBulk={selectedIds.includes(conversation.id)}
            onToggleSelected={() => onToggleBulkId(conversation.id)}
            onClick={() => onSelectConversation(conversation.id)}
            t={t}
          />
        ))}
      </div>
    </WorkQueueListPane>
  );
}

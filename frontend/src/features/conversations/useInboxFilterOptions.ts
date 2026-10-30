import { useMemo } from "react";

import { type InboxFilters } from "../../api/inbox";

import { channelOptions, priorityOptions } from "./conversationConstants";
import { channelLabel } from "./conversationUtils";

import type { useInboxQueries } from "./useInboxQueries";
import type { Translate } from "./conversationTypes";
type Args = {
  items: ReturnType<typeof useInboxQueries>["items"];
  conversations: ReturnType<typeof useInboxQueries>["conversations"];
  summary: ReturnType<typeof useInboxQueries>["summary"];
  bots: ReturnType<typeof useInboxQueries>["bots"];
  quickReplies: ReturnType<typeof useInboxQueries>["quickReplies"];
  filters: InboxFilters;
  quickReplySearch: string;
  t: Translate;
};
export function useInboxFilterOptions({
  items,
  conversations,
  summary,
  bots,
  quickReplies,
  filters,
  quickReplySearch,
  t,
}: Args) {
  const conversationCounts = useMemo(() => {
    const myTurn = items.filter((item) => item.assigned_to !== null).length;
    return {
      all: conversations.data?.count ?? summary.data?.total ?? items.length,
      unread: items.filter((item) => (item.unread_count || 0) > 0).length,
      attention: items.filter((item) => item.handoff_required).length,
      botDisabled: items.filter((item) => !item.bot_enabled).length,
      myTurn,
      unassigned: items.filter((item) => !item.assigned_to).length,
      closed: items.filter((item) => item.status === "closed").length,
      active: items.filter((item) => item.status !== "closed").length,
    };
  }, [items, conversations.data?.count, summary.data?.total]);
  const hasActiveFilters = useMemo(
    () =>
      Boolean(
        filters.bot ||
        filters.channel ||
        filters.priority ||
        filters.assigned_to ||
        filters.status ||
        filters.unread ||
        filters.handoff_required ||
        filters.bot_enabled,
      ),
    [filters],
  );
  const activeFilterSummary = useMemo(() => {
    const parts: string[] = [];
    if (filters.bot) parts.push(t("conversations.agent"));
    if (filters.channel) parts.push(channelLabel(filters.channel, t));
    if (filters.priority)
      parts.push(
        `${t("conversations.priority")}: ${t(`status.${filters.priority}`)}`,
      );
    if (filters.unread === "true")
      parts.push(t("conversations.unreadMessages"));
    if (filters.handoff_required === "true")
      parts.push(t("conversations.needsOperator"));
    if (filters.bot_enabled === "false")
      parts.push(t("conversations.botPaused"));
    if (filters.bot_enabled === "true")
      parts.push(t("conversations.botActive"));
    if (filters.assigned_to === "me")
      parts.push(t("conversations.assignedToMeFilter"));
    if (filters.assigned_to === "unassigned")
      parts.push(t("conversations.unassigned"));
    if (filters.status === "open") parts.push(t("conversations.active"));
    if (filters.status === "closed") parts.push(t("status.closed"));
    return parts;
  }, [filters, t]);
  const queueFilterOptions = useMemo(
    () => [
      {
        value: "all",
        label: `${t("conversations.queueAll")} (${conversationCounts.all})`,
      },
      {
        value: "new",
        label: `${t("conversations.unreadMessages")} (${summary.data?.unread ?? conversationCounts.unread})`,
      },
      {
        value: "attention",
        label: `${t("conversations.attention")} (${summary.data?.handoff_required ?? conversationCounts.attention})`,
      },
      {
        value: "paused",
        label: `${t("conversations.botPaused")} (${summary.data?.bot_paused ?? conversationCounts.botDisabled})`,
      },
      {
        value: "closed",
        label: `${t("status.closed")} (${conversationCounts.closed})`,
      },
    ],
    [
      conversationCounts.all,
      conversationCounts.attention,
      conversationCounts.botDisabled,
      conversationCounts.closed,
      conversationCounts.unread,
      summary.data?.bot_paused,
      summary.data?.handoff_required,
      summary.data?.unread,
      t,
    ],
  );
  const ownerFilterOptions = useMemo(
    () => [
      {
        value: "all",
        label: `${t("conversations.allManagers")} (${conversationCounts.all})`,
      },
      {
        value: "me",
        label: `${t("conversations.assignedToMeFilter")} (${summary.data?.assigned_to_me ?? 0})`,
      },
      {
        value: "unassigned",
        label: `${t("conversations.unassigned")} (${summary.data?.unassigned ?? conversationCounts.unassigned})`,
      },
    ],
    [
      conversationCounts.all,
      conversationCounts.unassigned,
      summary.data?.assigned_to_me,
      summary.data?.unassigned,
      t,
    ],
  );
  const agentFilterOptions = useMemo(
    () => [
      { value: "", label: t("conversations.allAgents") },
      ...(bots.data || []).map((bot) => ({ value: bot.id, label: bot.name })),
    ],
    [bots.data, t],
  );
  const localizedChannelOptions = useMemo(
    () =>
      channelOptions.map((option) => ({
        value: option.value,
        label: "labelKey" in option ? t(option.labelKey) : option.label,
      })),
    [t],
  );
  const localizedPriorityOptions = useMemo(
    () =>
      priorityOptions.map((option) => ({
        value: option.value,
        label: t(option.labelKey),
      })),
    [t],
  );
  const priorityActionOptions = useMemo(
    () => localizedPriorityOptions.filter((option) => option.value),
    [localizedPriorityOptions],
  );
  const quickReplyTemplates = useMemo(() => {
    const source = quickReplies.data || [];
    const search = quickReplySearch.trim().toLowerCase();
    if (!search) return source;
    return source.filter((template) =>
      `${template.title} ${template.text} ${template.category}`
        .toLowerCase()
        .includes(search),
    );
  }, [quickReplies.data, quickReplySearch]);
  const localizedSortOptions = useMemo(
    () => [
      { value: "latest", label: t("conversations.sortLatest") },
      { value: "unread", label: t("conversations.sortUnread") },
      { value: "first_response", label: t("conversations.sortFirstResponse") },
    ],
    [t],
  );
  const localizedStatusOptions = useMemo(
    () => [
      {
        value: "all",
        label: `${t("conversations.noFilter")} (${conversationCounts.all})`,
      },
      {
        value: "open",
        label: `${t("conversations.active")} (${conversationCounts.active})`,
      },
      {
        value: "closed",
        label: `${t("status.closed")} (${conversationCounts.closed})`,
      },
    ],
    [
      conversationCounts.active,
      conversationCounts.all,
      conversationCounts.closed,
      t,
    ],
  );
  return {
    conversationCounts,
    hasActiveFilters,
    activeFilterSummary,
    queueFilterOptions,
    ownerFilterOptions,
    agentFilterOptions,
    localizedChannelOptions,
    localizedPriorityOptions,
    priorityActionOptions,
    quickReplyTemplates,
    localizedSortOptions,
    localizedStatusOptions,
  };
}

import {
  InfiniteData,
  keepPreviousData,
  useInfiniteQuery,
  useQuery,
} from "@tanstack/react-query";

import { useMemo } from "react";

import { botsApi } from "../../api/bots";
import { businessConnectorsApi } from "../../api/connectors";
import { quickRepliesApi } from "../../api/quickReplies";
import {
  INBOX_MESSAGES_PAGE_SIZE,
  inboxApi,
  inboxQueryKeys,
  type InboxFilters,
  type PaginatedInboxMessageResponse,
} from "../../api/inbox";

import { realtimeIntervals, realtimeQueryOptions } from "../../lib/realtime";

import { getConversationTimestamp } from "./conversationUtils";

import type { InboxSort } from "./conversationTypes";
type Args = {
  businessId: number | undefined;
  canViewIntegrations: boolean;
  normalizedFilters: InboxFilters;
  sortBy: InboxSort;
  selectedId: number | null;
  userId: number | undefined;
};
export function useInboxQueries({
  businessId,
  canViewIntegrations,
  normalizedFilters,
  sortBy,
  selectedId,
  userId,
}: Args) {
  const summary = useQuery({
    queryKey: ["inbox-summary", businessId],
    queryFn: inboxApi.getSummary,
    refetchInterval: realtimeIntervals.inboxConversationsMs,
    ...realtimeQueryOptions,
  });
  const communicationConnectors = useQuery({
    queryKey: ["business-connectors", "inbox-readiness", businessId],
    queryFn: () => businessConnectorsApi.list({ business: businessId! }),
    enabled: Boolean(businessId && canViewIntegrations),
    retry: false,
  });
  const conversations = useQuery({
    queryKey: inboxQueryKeys.conversations(normalizedFilters),
    queryFn: () => inboxApi.listConversations(normalizedFilters),
    refetchInterval: realtimeIntervals.inboxConversationsMs,
    ...realtimeQueryOptions,
    placeholderData: keepPreviousData,
  });
  const bots = useQuery({
    queryKey: ["bots"],
    queryFn: botsApi.list,
  });
  const items = conversations.data?.results || [];
  const sortedItems = useMemo(() => {
    const source = [...items];
    if (sortBy === "unread") {
      source.sort((left, right) => {
        const unreadDiff = (right.unread_count || 0) - (left.unread_count || 0);
        if (unreadDiff !== 0) return unreadDiff;
        const leftDate = getConversationTimestamp(left.last_message_at);
        const rightDate = getConversationTimestamp(right.last_message_at);
        return rightDate - leftDate;
      });
      return source;
    }

    if (sortBy === "first_response") {
      source.sort((left, right) => {
        const leftDate = getConversationTimestamp(left.last_inbound_at);
        const rightDate = getConversationTimestamp(right.last_inbound_at);
        return leftDate - rightDate;
      });
      return source;
    }

    source.sort(
      (left, right) =>
        getConversationTimestamp(right.last_message_at) -
        getConversationTimestamp(left.last_message_at),
    );
    return source;
  }, [items, sortBy]);
  const selectedFromList = useMemo(
    () => sortedItems.find((item) => item.id === selectedId) || null,
    [sortedItems, selectedId],
  );
  const selectedConversation = useQuery({
    queryKey: ["inbox-conversation", selectedId],
    queryFn: () => inboxApi.getConversation(selectedId!),
    enabled: Boolean(selectedId && !selectedFromList),
    refetchInterval:
      selectedId && !selectedFromList
        ? realtimeIntervals.inboxConversationsMs
        : false,
    ...realtimeQueryOptions,
  });
  const selected = selectedFromList || selectedConversation.data || null;
  const context = useQuery({
    queryKey: ["inbox-context", userId, selected?.business, selected?.id],
    queryFn: () => inboxApi.getContext(selected!.id),
    enabled: Boolean(selected),
    retry: false,
    refetchInterval: realtimeIntervals.inboxConversationsMs,
  });
  const quickReplies = useQuery({
    queryKey: ["quick-replies", businessId, selected?.channel],
    queryFn: () =>
      quickRepliesApi.listAll({
        business: selected?.business || businessId,
        channel: selected?.channel || "all",
        is_active: true,
      }),
    enabled: Boolean(businessId && selected?.channel),
  });
  const messages = useInfiniteQuery<
    PaginatedInboxMessageResponse,
    Error,
    InfiniteData<PaginatedInboxMessageResponse>,
    ReturnType<typeof inboxQueryKeys.messages>,
    number | null
  >({
    queryKey: inboxQueryKeys.messages(selected?.id),
    queryFn: ({ pageParam }) =>
      inboxApi.listMessages(selected!.id, {
        limit: INBOX_MESSAGES_PAGE_SIZE,
        beforeId: pageParam ?? undefined,
      }),
    initialPageParam: null,
    getNextPageParam: (lastPage) => lastPage.next_before_id || undefined,
    enabled: Boolean(selected?.id),
    refetchInterval: selected?.id ? realtimeIntervals.inboxMessagesMs : false,
    ...realtimeQueryOptions,
  });
  const messageList = useMemo(() => {
    if (!messages.data) return [];
    return [...messages.data.pages].reverse().flatMap((page) => page.results);
  }, [messages.data]);
  return {
    summary,
    communicationConnectors,
    conversations,
    bots,
    items,
    sortedItems,
    selectedFromList,
    selectedConversation,
    selected,
    context,
    quickReplies,
    messages,
    messageList,
  };
}

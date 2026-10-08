import {
  InfiniteData,
  keepPreviousData,
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  BellDot,
  CheckSquare,
  Link2,
  Sparkles,
  UserRound,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  Navigate,
  Link,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router";

import { getApiErrorMessage, getApiFieldErrors } from "../../api/client";
import { botsApi } from "../../api/bots";
import { businessConnectorsApi } from "../../api/connectors";
import { quickRepliesApi } from "../../api/quickReplies";
import {
  INBOX_MESSAGES_PAGE_SIZE,
  inboxApi,
  inboxQueryKeys,
  type InboxConversation,
  type InboxFilters,
  type InboxMessage,
  type PaginatedInboxMessageResponse,
  type PipelineAction,
  type PipelineConfirmation,
} from "../../api/inbox";
import { useActionFeedback } from "../../components/actions/useActionFeedback";
import { usePageHeader } from "../../components/layout/PageHeaderContext";
import { WorkQueueLayout } from "../../components/layout/WorkQueueLayout";
import { useNotification } from "../../components/notifications/NotificationProvider";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Dialog, Drawer } from "../../components/ui/Overlay";
import { Select } from "../../components/ui/Select";
import { StatusBadge } from "../../components/ui/StatusBadge";
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "../../components/ui/StateViews";
import { Textarea } from "../../components/ui/Textarea";
import { cn } from "../../lib/cn";
import { useI18n } from "../../lib/i18n";
import { hasPermission } from "../../lib/permissions";
import { realtimeIntervals, realtimeQueryOptions } from "../../lib/realtime";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useAuth } from "../auth/AuthProvider";
import { ConversationListPane } from "./components/ConversationListPane";
import type { ActionMenuItem } from "../../components/ui/ActionMenu";
import { useMediaQuery } from "../../hooks/useMediaQuery";
import { InboxCustomerContext } from "./components/InboxCustomerContext";
import { appendReplyDraft, useInboxDraft } from "./hooks/useInboxDraft";
import { ConversationThreadPane } from "./components/ConversationThreadPane";
import { InboxMemoryControl } from "./components/InboxMemoryControl";
import { MessageDeliveryDetails } from "./components/MessageDeliveryDetails";
import { PipelineConfirmationDialog, type PipelineReview } from "./components/PipelineConfirmationDialog";
import {
  channelOptions,
  priorityOptions,
} from "./conversationConstants";
import {
  channelLabel,
  conversationTitle,
  getAutoPipelineInsight,
  getConversationTimestamp,
} from "./conversationUtils";
import { useConversationFilters } from "./hooks/useConversationFilters";

function asNumericId(value: string | undefined): number | null {
  const id = Number(value);
  return Number.isFinite(id) && id > 0 ? id : null;
}

function searchWithoutLegacyConversation(searchParams: URLSearchParams) {
  const params = new URLSearchParams(searchParams);
  params.delete("conversation");
  const query = params.toString();
  return query ? `?${query}` : "";
}

function isIntegrationsAction(href: string) {
  const path = href.split(/[?#]/, 1)[0].replace(/\/+$/, "");
  return path === "/app/integrations" || path.startsWith("/app/integrations/");
}

function createIdempotencyKey(scope: string) {
  const random = typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return `${scope}:${random}`;
}

export function ConversationsPage() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const { id: routeId } = useParams();
  const showNotification = useNotification();
  const { notifyError } = useActionFeedback();
  const { setPageHeader } = usePageHeader();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const routeSelectedId = asNumericId(routeId);
  const legacySelectedId = routeSelectedId
    ? null
    : Number(searchParams.get("conversation")) || null;
  const [selectedId, setSelectedId] = useState<number | null>(
    () => routeSelectedId || legacySelectedId || null,
  );
  const { activePreset, applyFilters, filters, normalizedFilters, sortBy } =
    useConversationFilters({
      searchParams,
      setSearchParams,
    });
  const [bulkMode, setBulkMode] = useState(false);
  const [mobileThreadOpen, setMobileThreadOpen] = useState(() =>
    Boolean(routeSelectedId || legacySelectedId),
  );
  const [inspectorOpen, setInspectorOpen] = useState(true);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [mobileInspectorOpen, setMobileInspectorOpen] = useState(false);
  const [addLinkOpen, setAddLinkOpen] = useState(false);
  const [automationOpen, setAutomationOpen] = useState(false);
  const desktopInspector = useMediaQuery("(min-width: 1280px)");
  const desktopThread = useMediaQuery("(min-width: 1024px)");
  const readSelectionRef = useRef<string | null>(null);
  const contextTriggerRef = useRef<HTMLButtonElement>(null);
  const retryKeys = useRef(new Map<number, string>());
  const [suggestedReply, setSuggestedReply] = useState("");

  const sendIdempotencyRef = useRef<{ conversationId: number; text: string; key: string } | null>(null);
  const [quickRepliesOpen, setQuickRepliesOpen] = useState(false);
  const [pipelineReview, setPipelineReview] = useState<PipelineReview | null>(null);
  const [quickReplySearch, setQuickReplySearch] = useState("");
  const [crmLinkModal, setCrmLinkModal] = useState<
    "client" | "lead" | "deal" | null
  >(null);
  const [crmLinkSearch, setCrmLinkSearch] = useState("");
  const [taskModalOpen, setTaskModalOpen] = useState(false);
  const [taskDraft, setTaskDraft] = useState({
    title: "",
    description: "",
    priority: "normal" as "low" | "normal" | "high" | "urgent",
    due_at: "",
  });
  const composerRef = useRef<HTMLTextAreaElement | null>(null);
  const messageScrollRef = useRef<HTMLDivElement | null>(null);
  const messageEndRef = useRef<HTMLDivElement | null>(null);
  const { user } = useAuth();
  const { business } = useActiveBusiness();
  const businessId = business?.id;
  const canViewIntegrations = hasPermission(
    user,
    business?.id,
    "integrations",
    "view",
  );
  useEffect(() => {
    if (!routeSelectedId || routeSelectedId === selectedId) return;
    setSelectedId(routeSelectedId);
    setMobileThreadOpen(true);
  }, [routeSelectedId, selectedId]);

  function resizeComposer() {
    const composer = composerRef.current;
    if (!composer) return;
    const maxHeight = window.matchMedia("(max-width: 640px)").matches
      ? 120
      : 160;
    composer.style.height = "auto";
    composer.style.height = `${Math.min(composer.scrollHeight, maxHeight)}px`;
    composer.style.overflowY =
      composer.scrollHeight > maxHeight ? "auto" : "hidden";
  }

  function setNotice(
    message: string | null,
    tone: "success" | "info" | "warning" | "danger" = "info",
  ) {
    if (!message) return;
    showNotification({ message, tone });
  }

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

  const canSuggestAi = hasPermission(
    user,
    selected?.business,
    "ai_assistant",
    "suggest",
  );
  const canSuggestAiPipeline = hasPermission(
    user,
    selected?.business,
    "ai_pipeline",
    "suggest",
  );
  const canRunAiPipeline = hasPermission(
    user,
    selected?.business,
    "ai_pipeline",
    "execute",
  );
  const { draft, draftKey, setDraft, clearSentDraft } = useInboxDraft(user?.id, selected?.business, selected?.id);
  const currentConversationRef = useRef(selected?.id);
  currentConversationRef.current = selected?.id;
  const context = useQuery({
    queryKey: ["inbox-context", user?.id, selected?.business, selected?.id],
    queryFn: () => inboxApi.getContext(selected!.id),
    enabled: Boolean(selected), retry: false,
    refetchInterval: realtimeIntervals.inboxConversationsMs,
  });
  const canUpdate = context.data?.actions.update ?? hasPermission(user, selected?.business, "conversations", "update");
  useEffect(() => {
    setSuggestedReply("");
    setMobileInspectorOpen(false);
    setCrmLinkModal(null);
    setAddLinkOpen(false);
    setAutomationOpen(false);
    setPipelineReview(null);
    setTaskModalOpen(false);
    setQuickRepliesOpen(false);
  }, [user?.id, selected?.business, selected?.id]);

  const quickReplies = useQuery({
    queryKey: ["quick-replies", businessId, selected?.channel],
    queryFn: () =>
      quickRepliesApi.list({
        channel: selected?.channel || "all",
        is_active: true,
      }),
    enabled: Boolean(businessId && selected?.channel),
  });

  const linkCandidates = useQuery({
    queryKey: ["inbox-link-candidates", user?.id, selected?.business, selected?.id, crmLinkModal, crmLinkSearch],
    queryFn: () => inboxApi.linkCandidates(selected!.id, crmLinkModal!, crmLinkSearch),
    enabled: Boolean(selected && crmLinkModal && context.data?.actions[`link_${crmLinkModal}`]),
    retry: false,
  });

  useEffect(() => {
    setPageHeader({ title: t("nav.conversations") });
    return () => setPageHeader(null);
  }, [setPageHeader, t]);

  useEffect(() => {
    if (selectedId || conversations.isLoading || !items.length) return;
    const slaOverdue = sortedItems.find(
      (item) => item.sla_overdue || (item.sla_overdue_minutes || 0) > 0,
    );
    const handoff = sortedItems.find((item) => item.handoff_required);
    const unread = sortedItems.find((item) => (item.unread_count || 0) > 0);
    const priority =
      slaOverdue ||
      handoff ||
      unread ||
      sortedItems[0];
    if (!priority) return;
    setSelectedId(priority.id);
    const params = new URLSearchParams(searchParams);
    params.delete("conversation");
    const query = params.toString();
    navigate(`/app/conversations/${priority.id}${query ? `?${query}` : ""}`, {
      replace: true,
    });
  }, [
    conversations.isLoading,
    navigate,
    sortedItems,
    searchParams,
    selectedId,
  ]);

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
      parts.push(`${t("conversations.priority")}: ${t(`status.${filters.priority}`)}`);
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

  function handleSortChange(sort: string) {
    const nextSort =
      sort === "latest"
        ? "latest"
        : sort === "unread"
          ? "unread"
          : "first_response";
    applyFilters(filters, activePreset, nextSort);
  }

  function handleQueueChange(value: string) {
    const next: InboxFilters = {
      ...filters,
      unread: undefined,
      handoff_required: undefined,
      bot_enabled: undefined,
      status: "",
    };
    if (value === "new") next.unread = "true";
    if (value === "attention") next.handoff_required = "true";
    if (value === "paused") next.bot_enabled = "false";
    if (value === "closed") next.status = "closed";
    applyFilters(
      next,
      value === "all" &&
        !next.assigned_to &&
        !next.bot &&
        !next.channel &&
        !next.priority
        ? "all"
        : "custom",
    );
    setSelectedIds([]);
    setBulkMode(false);
  }

  function handleOwnerChange(value: string) {
    const next: InboxFilters = {
      ...filters,
      assigned_to: value === "all" ? undefined : value,
    };
    applyFilters(
      next,
      value === "all" &&
        !next.unread &&
        !next.handoff_required &&
        !next.bot_enabled &&
        !next.status &&
        !next.bot &&
        !next.channel &&
        !next.priority
        ? "all"
        : "custom",
    );
    setSelectedIds([]);
    setBulkMode(false);
  }

  function updateFilters(next: InboxFilters) {
    applyFilters(next, "custom");
    setSelectedIds([]);
    setBulkMode(false);
  }

  function resetConversationFilters() {
    const next: InboxFilters = { search: filters.search };
    applyFilters(next, "all", "latest");
    setSelectedIds([]);
    setBulkMode(false);
  }

  function selectConversation(id: number) {
    setSelectedId(id);
    setMobileThreadOpen(true);
    const params = new URLSearchParams(searchParams);
    params.delete("conversation");
    const query = params.toString();
    navigate(`/app/conversations/${id}${query ? `?${query}` : ""}`);
    const conversation = items.find((item) => item.id === id);
    if (id === selected?.id && context.data?.actions.update && (conversation?.unread_count || 0) > 0) {
      readSelectionRef.current = `${user?.id}:${selected.business}:${selected.id}`;
      markReadMutation.mutate(id);
    }
  }

  const invalidateInbox = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["inbox-summary"] }),
      queryClient.invalidateQueries({
        queryKey: ["inbox-summary"],
        exact: false,
      }),
      queryClient.invalidateQueries({ queryKey: ["inbox-conversations"] }),
      queryClient.invalidateQueries({ queryKey: ["inbox-context"] }),
      queryClient.invalidateQueries({
        queryKey: ["inbox-conversation", selected?.id],
      }),
      queryClient.invalidateQueries({
        queryKey: inboxQueryKeys.messages(selected?.id),
      }),
      queryClient.invalidateQueries({
        queryKey: ["inbox-summary", businessId],
      }),
      queryClient.invalidateQueries({ queryKey: ["notifications-summary"] }),
      queryClient.invalidateQueries({ queryKey: ["notifications"] }),
    ]);
  };

  function toggleBulkId(id: number) {
    setSelectedIds((current) =>
      current.includes(id)
        ? current.filter((item) => item !== id)
        : [...current, id],
    );
  }

  function selectVisibleConversations() {
    setBulkMode(true);
    setSelectedIds(sortedItems.map((item) => item.id));
  }

  function resetBulkSelection() {
    setBulkMode(false);
    setSelectedIds([]);
  }

  function appendSystemEvent(conversationId: number, text: string) {
    const now = new Date().toISOString();
    const eventMessage: InboxMessage = {
      id: -Date.now(),
      conversation: conversationId,
      direction: "outbound",
      sender_type: "system",
      text,
      payload_json: { source: "local_status_event" },
      status: "sent",
      sent_at: now,
      delivered_at: null,
      read_at: null,
      created_at: now,
      attachments: [],
    };

    queryClient.setQueryData<InfiniteData<PaginatedInboxMessageResponse>>(
      inboxQueryKeys.messages(conversationId),
      (current) => {
        if (!current || !current.pages.length) {
          return current;
        }

        const eventTime = new Date(now).getTime();
        const hasRecentDuplicate = current.pages.some((page) =>
          page.results.some((message) => {
            if (message.sender_type !== "system" || message.text !== text)
              return false;
            const messageTime = new Date(
              message.created_at || message.sent_at || 0,
            ).getTime();
            return (
              Number.isFinite(messageTime) &&
              Math.abs(eventTime - messageTime) < 10_000
            );
          }),
        );

        if (hasRecentDuplicate) {
          return current;
        }

        const nextPages = [...current.pages];
        const latestPage = nextPages[0];
        nextPages[0] = {
          ...latestPage,
          results: [...latestPage.results, eventMessage],
        };

        return {
          ...current,
          pages: nextPages,
        };
      },
    );
  }

  const assignMutation = useMutation({
    mutationFn: inboxApi.assignToMe,
    onSuccess: async (_data, conversationId) => {
      setNotice(null);
      await invalidateInbox();
      appendSystemEvent(
        Number(conversationId),
        t("conversations.systemAssignedToMe"),
      );
    },
    onError: (error) => notifyError(error),
  });

  const handoffMutation = useMutation({
    mutationFn: inboxApi.handoff,
    onSuccess: async (_data, variables) => {
      setNotice(null);
      await invalidateInbox();
      appendSystemEvent(
        Number(variables.conversationId),
        t("conversations.systemHandoff"),
      );
    },
    onError: (error) => notifyError(error),
  });

  const markReadMutation = useMutation({
    mutationFn: inboxApi.markRead,
    onSuccess: async () => {
      await invalidateInbox();
    },
    onError: (error) => notifyError(error),
  });

  useEffect(() => {
    if (!selected || (!desktopThread && !mobileThreadOpen)) {
      readSelectionRef.current = null;
      return;
    }
    if (!messages.isSuccess || !context.data?.actions.update) return;
    const key = `${user?.id}:${selected.business}:${selected.id}`;
    if (readSelectionRef.current === key) return;
    // Only mark on opening: an explicit "unread" action must survive polling.
    readSelectionRef.current = key;
    if ((selected.unread_count || 0) > 0) markReadMutation.mutate(selected.id);
  }, [selected, user?.id, desktopThread, mobileThreadOpen, messages.isSuccess, context.data?.actions.update, markReadMutation.mutate]);

  const markUnreadMutation = useMutation({
    mutationFn: inboxApi.markUnread,
    onSuccess: async () => {
      setNotice(t("conversations.markedUnread"));
      await invalidateInbox();
    },
    onError: (error) => notifyError(error),
  });

  const setPriorityMutation = useMutation({
    mutationFn: inboxApi.setPriority,
    onSuccess: async () => {
      setNotice(t("conversations.priorityUpdated"));
      await invalidateInbox();
    },
    onError: (error) => notifyError(error),
  });

  const toggleBotMutation = useMutation({
    mutationFn: inboxApi.toggleBot,
    onSuccess: async (_data, variables) => {
      setNotice(null);
      await invalidateInbox();
      appendSystemEvent(
        Number(variables.conversationId),
        variables.botEnabled
          ? t("conversations.systemBotEnabled")
          : t("conversations.systemBotPaused"),
      );
    },
    onError: (error) => notifyError(error),
  });

  const closeMutation = useMutation({
    mutationFn: inboxApi.closeConversation,
    onSuccess: async (_data, variables) => {
      setNotice(null);
      await invalidateInbox();
      appendSystemEvent(
        Number(variables.conversationId),
        t("conversations.systemClosed"),
      );
    },
    onError: (error) => notifyError(error),
  });

  const reopenMutation = useMutation({
    mutationFn: inboxApi.reopenConversation,
    onSuccess: async (_data, conversationId) => {
      setNotice(null);
      await invalidateInbox();
      appendSystemEvent(
        Number(conversationId),
        t("conversations.systemReopened"),
      );
    },
    onError: (error) => notifyError(error),
  });

  const suggestMutation = useMutation({
    mutationFn: (conversationId: number) => {
      if (!canSuggestAi) throw new Error(t("conversations.aiReplyForbidden"));
      return inboxApi.suggestReply(conversationId);
    },
    onSuccess: (data, conversationId) => {
      if (currentConversationRef.current !== conversationId) return;
      setSuggestedReply(data.suggested_reply);
      setNotice(t("conversations.aiDraftReady"));
    },
    onError: (error) =>
      notifyError(error, {
        fallbackMessage: t("conversations.aiReplyForbidden"),
      }),
  });

  const qualifyMutation = useMutation({
    mutationFn: (conversationId: number) => {
      if (!canSuggestAiPipeline)
        throw new Error(t("conversations.aiPipelinePreviewForbidden"));
      return inboxApi.qualifyConversation(conversationId);
    },
    onSuccess: async (result) => {
      setNotice(
        t("conversations.qualificationPreviewReady", {
          intent: result.qualification.intent,
          confidence: Math.round(result.qualification.confidence * 100),
        }),
      );
      await invalidateInbox();
    },
    onError: (error) =>
      notifyError(error, {
        fallbackMessage: t("conversations.aiPipelinePreviewForbidden"),
      }),
  });

  const sendMutation = useMutation({
    mutationFn: (payload: Parameters<typeof inboxApi.sendMessage>[0] & { draftKey: string | null }) => inboxApi.sendMessage(payload),
    onSuccess: async (_result, variables) => {
      sendIdempotencyRef.current = null;
      clearSentDraft(variables.draftKey, variables.text);
      if (currentConversationRef.current === Number(variables.conversationId)) setSuggestedReply("");
      setNotice(t("conversations.replySent"), "success");
      await invalidateInbox();
    },
    onError: (error) =>
      notifyError(error, { focusTarget: composerRef }),
  });

  const retryMessageMutation = useMutation({
    mutationFn: inboxApi.retryMessage,
    onSuccess: async (_result, variables) => {
      retryKeys.current.delete(Number(variables.messageId));
      setNotice(t("conversations.messageRetried"), "success");
      await invalidateInbox();
    },
    onError: (error) => notifyError(error),
  });

  const createClientMutation = useMutation({
    mutationFn: inboxApi.createClient,
    onSuccess: async (result) => {
      if (result.requires_confirmation && result.duplicates.length) {
        setNotice(
          t("conversations.duplicateClientShort", {
            list: result.duplicates
              .map((item) => `#${item.id} ${item.full_name}`)
              .join(", "),
          }),
        );
        return;
      }
      setCrmLinkModal(null);
      setNotice(
        result.created
          ? t("conversations.clientCreatedShort")
          : t("conversations.clientAlreadyLinked"),
      );
      await Promise.all([
        invalidateInbox(),
        queryClient.invalidateQueries({ queryKey: ["clients"] }),
      ]);
    },
    onError: (error) => notifyError(error),
  });

  const linkClientMutation = useMutation({
    mutationFn: inboxApi.linkClient,
    onSuccess: async () => {
      setNotice(t("conversations.clientLinkedShort"));
      setCrmLinkModal(null);
      await invalidateInbox();
    },
    onError: (error) => notifyError(error),
  });

  const createLeadMutation = useMutation({
    mutationFn: inboxApi.createLead,
    onSuccess: async () => {
      setAddLinkOpen(false);
      setNotice(t("conversations.leadCreatedShort"));
      await Promise.all([
        invalidateInbox(),
        queryClient.invalidateQueries({ queryKey: ["leads"] }),
      ]);
    },
    onError: (error) => notifyError(error),
  });

  const linkLeadMutation = useMutation({
    mutationFn: inboxApi.linkLead,
    onSuccess: async () => {
      setNotice(t("conversations.leadLinkedShort"));
      setCrmLinkModal(null);
      await invalidateInbox();
    },
    onError: (error) => notifyError(error),
  });

  const createDealMutation = useMutation({
    mutationFn: inboxApi.createDeal,
    onSuccess: async () => {
      setAddLinkOpen(false);
      setNotice(t("conversations.dealCreatedShort"));
      await Promise.all([
        invalidateInbox(),
        queryClient.invalidateQueries({ queryKey: ["deals"] }),
      ]);
    },
    onError: (error) => notifyError(error),
  });

  const linkDealMutation = useMutation({
    mutationFn: inboxApi.linkDeal,
    onSuccess: async () => {
      setNotice(t("conversations.dealLinkedShort"));
      setCrmLinkModal(null);
      await invalidateInbox();
    },
    onError: (error) => notifyError(error),
  });

  const createTaskMutation = useMutation({
    mutationFn: inboxApi.createTask,
    onSuccess: async () => {
      setNotice(t("conversations.taskCreatedShort"), "success");
      setTaskModalOpen(false);
      await Promise.all([queryClient.invalidateQueries({ queryKey: ["tasks"] }), invalidateInbox()]);
    },
    onError: (error) => notifyError(error),
  });

  const runPipelineMutation = useMutation({
    mutationFn: (payload: PipelineConfirmation) => {
      if (!canRunAiPipeline)
        throw new Error(t("conversations.aiPipelineRunForbidden"));
      return inboxApi.runPipeline(payload);
    },
    onSuccess: async (result) => {
      const created = Object.entries(result.created)
        .filter(([, value]) => value)
        .map(([key]) => t(`conversations.pipelineCreated.${key}`))
        .join(", ");
      const aiSuffix = result.qualification
        ? t("conversations.pipelineAiSuffix", {
            intent: result.qualification.intent,
            confidence: Math.round(result.qualification.confidence * 100),
          })
        : "";
      setNotice(
        created
          ? t("conversations.pipelineUpdated", { created, ai: aiSuffix })
          : t("conversations.pipelineAlreadyLinked", { ai: aiSuffix }),
      );
      setPipelineReview(null);
      await Promise.all([
        invalidateInbox(),
        queryClient.invalidateQueries({ queryKey: ["clients"] }),
        queryClient.invalidateQueries({ queryKey: ["leads"] }),
        queryClient.invalidateQueries({ queryKey: ["deals"] }),
        queryClient.invalidateQueries({ queryKey: ["tasks"] }),
      ]);
    },
    onError: (error) => {
      if (getApiFieldErrors(error).preview_id) {
        setNotice(t("conversations.pipelinePreviewExpired"), "warning");
      } else {
        notifyError(error, {
          fallbackMessage: t("conversations.aiPipelineRunForbidden"),
        });
      }
    },
  });

  const bulkMutation = useMutation({
    mutationFn: async (
      action: "markRead" | "assign" | "handoff" | "pauseBot" | "close",
    ) => {
      const ids = [...selectedIds];
      if (action === "markRead") {
        await Promise.all(ids.map((id) => inboxApi.markRead(id)));
      }
      if (action === "assign") {
        await Promise.all(ids.map((id) => inboxApi.assignToMe(id)));
      }
      if (action === "handoff") {
        await Promise.all(
          ids.map((id) =>
            inboxApi.handoff({
              conversationId: id,
              reason: "bulk_handoff_from_inbox",
            }),
          ),
        );
      }
      if (action === "pauseBot") {
        await Promise.all(
          ids.map((id) =>
            inboxApi.toggleBot({ conversationId: id, botEnabled: false }),
          ),
        );
      }
      if (action === "close") {
        await Promise.all(
          ids.map((id) =>
            inboxApi.closeConversation({
              conversationId: id,
              reason: "bulk_closed_from_inbox",
            }),
          ),
        );
      }
      return { action, count: ids.length };
    },
    onSuccess: async ({ count }) => {
      setNotice(t("conversations.bulkDone", { count }));
      resetBulkSelection();
      await invalidateInbox();
    },
    onError: (error) => notifyError(error),
  });

  const pageError =
    summary.error ||
    conversations.error ||
    selectedConversation.error ||
    messages.error;
  const unavailableChannelCount = (communicationConnectors.data || []).filter(
    (connector) =>
      connector.capability === "communications" &&
      ["error", "failed", "needs_attention", "expired_credentials"].includes(
        connector.status,
      ),
  ).length;
  const priorityActions = (summary.data?.next_actions || []).filter(
    (action) => action.code !== "connect_channel" && (canViewIntegrations || !isIntegrationsAction(action.href)),
  );
  const channelAgent = (bots.data || []).find((bot) => bot.business === businessId && bot.scenario !== "crm");
  const connectChannelAction = canViewIntegrations && hasPermission(user, businessId, "ai_automation", "view") ? (
    <Link
      to={channelAgent ? `/app/ai-agents/${channelAgent.id}/channels` : "/app/ai-agents"}
      className="platforma-focus-ring inline-flex min-h-10 items-center justify-center rounded-control bg-brand-500 px-4 py-2 text-sm font-bold text-white shadow-xs transition hover:bg-brand-600"
    >
      {t("conversations.nextAction.connect_channel")}
    </Link>
  ) : undefined;
  function sendReply() {
    const text = draft.trim();
    if (!selected || !text || !canUpdate || selected.status !== "open" || sendMutation.isPending) return;
    const previousRequest = sendIdempotencyRef.current;
    const idempotencyKey = previousRequest?.conversationId === selected.id && previousRequest.text === text
      ? previousRequest.key
      : createIdempotencyKey(`inbox:send:${selected.id}`);
    sendIdempotencyRef.current = { conversationId: selected.id, text, key: idempotencyKey };
    sendMutation.mutate({ conversationId: selected.id, text, idempotencyKey, draftKey });
  }

  function insertQuickReply(text: string) {
    setDraft(current => appendReplyDraft(current, text));
    setQuickRepliesOpen(false);
    window.requestAnimationFrame(() => composerRef.current?.focus());
  }

  function createLinkedLead() {
    if (!selected) return;
    createLeadMutation.mutate({
      conversationId: selected.id,
      message: lastCustomerMessage?.text || undefined,
    });
  }

  function createLinkedDeal() {
    if (!selected) return;
    createDealMutation.mutate({
      conversationId: selected.id,
      title: t("conversations.pipelineDealTitle", {
        title: conversationTitle(selected, t),
      }),
    });
  }

  function createLinkedTask() {
    if (!selected) return;
    setTaskDraft({
      title: t("conversations.followUpTaskTitle", {
        title: conversationTitle(selected, t),
      }),
      description: lastCustomerMessage?.text || "",
      priority:
        selected.priority === "urgent" ||
        selected.priority === "high" ||
        selected.priority === "low"
          ? selected.priority
          : "normal",
      due_at: "",
    });
    setTaskModalOpen(true);
  }

  function submitTaskFromInspector() {
    if (!selected) return;
    createTaskMutation.mutate({
      conversationId: selected.id,
      title: taskDraft.title,
      description: taskDraft.description,
      priority: taskDraft.priority,
      due_at: taskDraft.due_at
        ? new Date(taskDraft.due_at).toISOString()
        : null,
    });
  }

  function openCrmLinkModal(target: "client" | "lead" | "deal") {
    linkClientMutation.reset();
    linkLeadMutation.reset();
    linkDealMutation.reset();
    createClientMutation.reset();
    setCrmLinkSearch("");
    setCrmLinkModal(target);
  }

  function linkClientToConversation(clientId: number) {
    if (!selected) return;
    linkClientMutation.mutate({ conversationId: selected.id, clientId });
  }

  function linkLeadToConversation(leadId: number) {
    if (!selected) return;
    linkLeadMutation.mutate({ conversationId: selected.id, leadId });
  }

  function linkDealToConversation(dealId: number) {
    if (!selected) return;
    linkDealMutation.mutate({ conversationId: selected.id, dealId });
  }

  function previewSelectedPipeline() {
    if (!selected) return;
    qualifyMutation.mutate(selected.id);
  }

  function runSelectedPipeline() {
    if (!selected) return;
    if (!selectedInsight?.previewId) {
      previewSelectedPipeline();
      return;
    }
    runPipelineMutation.reset();
    setPipelineReview({
      conversationId: selected.id,
      previewId: selectedInsight.previewId,
      summary: selectedInsight.summary,
      proposedActions: selectedInsight.proposedActions,
    });
  }

  const selectedInsight = selected ? getAutoPipelineInsight(selected) : null;
  const canApplyPipeline = canRunAiPipeline && Boolean(selectedInsight);
  const pipelineAllowedActions: PipelineAction[] = ([
    ["create_lead", "leads"], ["create_task", "tasks"], ["create_deal", "deals"],
  ] as const).filter(([, resource]) => hasPermission(user, selected?.business, resource, "create"))
    .map(([action]) => action);
  const messageList = useMemo(() => {
    if (!messages.data) return [];
    return [...messages.data.pages].reverse().flatMap((page) => page.results);
  }, [messages.data]);
  const canLoadMoreMessages = Boolean(messages.hasNextPage);
  const lastMessage = messageList[messageList.length - 1];
  const lastCustomerMessage = [...messageList].reverse().find(message =>
    message.direction === "inbound" && message.sender_type !== "system" && message.text?.trim(),
  );
  const lastMessageSignature = lastMessage
    ? `${lastMessage.id}:${lastMessage.created_at || lastMessage.sent_at || ""}:${lastMessage.text || ""}`
    : "";

  useEffect(() => {
    if (!selected?.id) return;
    const frame = window.requestAnimationFrame(() => {
      if (messageEndRef.current) {
        messageEndRef.current.scrollIntoView({
          block: "end",
          behavior: "smooth",
        });
        return;
      }
      messageScrollRef.current?.scrollTo({
        top: messageScrollRef.current.scrollHeight,
        behavior: "smooth",
      });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [lastMessageSignature, messageList.length, selected?.id]);

  useEffect(() => {
    resizeComposer();
  }, [draft]);

  if (legacySelectedId) {
    return (
      <Navigate
        to={`/app/conversations/${legacySelectedId}${searchWithoutLegacyConversation(searchParams)}`}
        replace
      />
    );
  }

  if (pageError) {
    return (
      <div data-testid="inbox-error-state">
        <ErrorState
          error={pageError} message={getApiErrorMessage(pageError)}
          action={
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => {
                void Promise.all([
                  summary.refetch(),
                  conversations.refetch(),
                  selectedConversation.refetch(),
                  messages.refetch(),
                ]);
              }}
            >
              {t("common.retry")}
            </Button>
          }
        />
      </div>
    );
  }

  function closeContext() {
    setMobileInspectorOpen(false);
    if (desktopInspector) { setInspectorOpen(false); contextTriggerRef.current?.focus(); }
  }
  const contextMenu: ActionMenuItem[] = (["client", "lead", "deal"] as const)
    .filter(kind => context.data?.[kind].state === "available" && context.data.actions[`link_${kind}`])
    .map(kind => ({ key: kind, label: t(`conversations.changeLink.${kind}`), icon: Link2, onSelect: () => openCrmLinkModal(kind) }));
  const threadMenu: ActionMenuItem[] = [
    ...(canUpdate ? [{ key: "unread", label: t("conversations.markUnreadAction"), icon: BellDot, onSelect: () => selected && markUnreadMutation.mutate(selected.id) },
      ...localizedPriorityOptions.map(option => ({ key: `priority-${option.value}`, label: `${t("conversations.priority")}: ${option.label}`, icon: BellDot, disabled: setPriorityMutation.isPending || selected?.priority === option.value, onSelect: () => selected && setPriorityMutation.mutate({ conversationId: selected.id, priority: option.value as NonNullable<InboxConversation["priority"]> }) }))] : []),
    ...(context.data?.actions.create_task ? [{ key: "task", label: t("conversations.createTask"), icon: CheckSquare, onSelect: createLinkedTask }] : []),
    ...(canSuggestAiPipeline || canRunAiPipeline ? [{ key: "automation", label: t("conversations.crmAutomation"), icon: Sparkles, onSelect: () => setAutomationOpen(true) }] : []),
  ];
  const customerContext = <InboxCustomerContext data={context.data} loading={context.isLoading} error={context.error} retrying={context.isFetching} menuItems={contextMenu} inDrawer={!desktopInspector} onRetry={() => void context.refetch()} onClose={closeContext} onNavigate={href => { setMobileInspectorOpen(false); navigate(href); }} onLinkClient={() => openCrmLinkModal("client")} onAddLink={() => setAddLinkOpen(true)} />;

  return (
    <div
      data-testid="inbox-workspace-ready"
      className="h-[calc(100dvh-var(--app-header-height)-2rem-var(--inbox-mobile-nav))] overflow-hidden"
    >
      <WorkQueueLayout
        style={{ height: "100%", minHeight: 0 }}
        className={cn(
          "overflow-hidden border border-platforma-border shadow-soft lg:grid-cols-[288px_minmax(0,1fr)]",
          inspectorOpen
            ? selected ? "xl:grid-cols-[288px_minmax(0,1fr)_320px]" : "xl:grid-cols-[288px_minmax(0,1fr)_284px]"
            : "xl:grid-cols-[288px_minmax(0,1fr)]",
        )}
      >
        <ConversationListPane
          connectChannelAction={connectChannelAction}
          mobileThreadOpen={mobileThreadOpen}
          filters={filters}
          sortBy={sortBy}
          hasActiveFilters={hasActiveFilters}
          activeFilterSummary={activeFilterSummary}
          queueFilterOptions={queueFilterOptions}
          ownerFilterOptions={ownerFilterOptions}
          agentFilterOptions={agentFilterOptions}
          channelOptions={localizedChannelOptions}
          priorityOptions={localizedPriorityOptions}
          statusOptions={localizedStatusOptions}
          sortOptions={localizedSortOptions}
          onQueueChange={handleQueueChange}
          onOwnerChange={handleOwnerChange}
          onFilterChange={updateFilters}
          onSortChange={handleSortChange}
          onReset={resetConversationFilters}
          items={items}
          sortedItems={sortedItems}
          selectedId={selected?.id}
          loading={conversations.isLoading || selectedConversation.isLoading}
          bulkMode={bulkMode}
          selectedIds={selectedIds}
          onSelectVisible={selectVisibleConversations}
          onResetBulk={resetBulkSelection}
          onBulkAction={(action) => bulkMutation.mutate(action)}
          bulkPending={bulkMutation.isPending}
          onToggleBulkId={toggleBulkId}
          onSelectConversation={selectConversation}
          priorityActions={priorityActions}
          unavailableChannelCount={unavailableChannelCount}
          connectorReadinessLoading={
            canViewIntegrations && communicationConnectors.isLoading
          }
          connectorReadinessError={
            canViewIntegrations && communicationConnectors.isError
          }
          connectorReadinessRetrying={communicationConnectors.isFetching}
          onRetryConnectorReadiness={() => communicationConnectors.refetch()}
          canViewIntegrations={canViewIntegrations}
          t={t}
        />

        <ConversationThreadPane
          connectChannelAction={connectChannelAction}
          canUpdate={canUpdate}
          headerActions={<>
            <Button ref={contextTriggerRef} variant="ghost" size="sm" onClick={() => desktopInspector ? setInspectorOpen(state => !state) : setMobileInspectorOpen(true)} aria-expanded={desktopInspector ? inspectorOpen : mobileInspectorOpen}>
              <UserRound size={16} />{t("conversations.aboutClient")}
            </Button>
            {selected ? <InboxMemoryControl key={selected.id} conversation={selected} items={threadMenu} /> : null}
          </>}
          aiActions={<>
              {canSuggestAi ? <Button variant="ghost" size="sm" onClick={() => selected && suggestMutation.mutate(selected.id)} disabled={!canUpdate || selected?.status !== "open"} isLoading={suggestMutation.isPending}><Sparkles size={16} />{t("conversations.prepareReply")}</Button> : null}
              {suggestedReply ? <Button variant="secondary" size="sm" disabled={!canUpdate || selected?.status !== "open"} onClick={() => { insertQuickReply(suggestedReply); setSuggestedReply(""); }}>{t("conversations.useSuggestedReply")}</Button> : null}
            {suggestMutation.isError && suggestMutation.variables === selected?.id ? <p role="alert" className="w-full text-xs text-platforma-danger">{getApiErrorMessage(suggestMutation.error)}</p> : null}
            {suggestedReply ? <p className="max-h-32 w-full overflow-y-auto whitespace-pre-wrap text-sm text-platforma-text">{suggestedReply}</p> : null}
          </>}
          renderDelivery={message => <MessageDeliveryDetails message={message} canRetry={canUpdate} retryPending={retryMessageMutation.isPending && retryMessageMutation.variables?.messageId === message.id} onRetry={() => {
            if (!selected || retryMessageMutation.isPending) return;
            let key = retryKeys.current.get(message.id);
            if (!key) { key = createIdempotencyKey(`inbox:retry:${message.id}`); retryKeys.current.set(message.id, key); }
            retryMessageMutation.mutate({ conversationId: selected.id, messageId: message.id, idempotencyKey: key });
          }} t={t} />}
          selected={selected}
          mobileThreadOpen={mobileThreadOpen}
          onMobileClose={() => setMobileThreadOpen(false)}
          messageScrollRef={messageScrollRef}
          messageEndRef={messageEndRef}
          messagesLoading={messages.isLoading || selectedConversation.isLoading}
          messageList={messageList}
          canLoadMoreMessages={canLoadMoreMessages}
          isFetchingNextPage={messages.isFetchingNextPage}
          onLoadMoreMessages={() => {
            void messages.fetchNextPage();
          }}
          draft={draft}
          composerRef={composerRef}
          sendPending={sendMutation.isPending}
          onDraftChange={setDraft}
          onResizeComposer={resizeComposer}
          onOpenQuickReplies={() => {
            setQuickReplySearch("");
            setQuickRepliesOpen(true);
          }}
          onSendReply={sendReply}
          onAssign={() => selected && assignMutation.mutate(selected.id)}
          assignPending={assignMutation.isPending}
          onToggleBot={() =>
            selected &&
            toggleBotMutation.mutate({
              conversationId: selected.id,
              botEnabled: !selected.bot_enabled,
            })
          }
          toggleBotPending={toggleBotMutation.isPending}
          canToggleBot={canSuggestAi && hasPermission(user, selected?.business, "conversations", "update")}
          onCloseConversation={() =>
            selected &&
            closeMutation.mutate({
              conversationId: selected.id,
              reason: "closed_from_inbox",
            })
          }
          closePending={closeMutation.isPending}
          onReopenConversation={() =>
            selected && reopenMutation.mutate(selected.id)
          }
          reopenPending={reopenMutation.isPending}
          t={t}
        />

        <aside className={cn("hidden min-h-0 flex-col border-l border-platforma-border xl:flex", !inspectorOpen && "xl:hidden")}>
          {selected ? customerContext : <div className="grid flex-1 place-items-center bg-surface-muted p-3 text-center text-sm font-bold text-platforma-muted">{t("conversations.selectContext")}</div>}
        </aside>
      </WorkQueueLayout>

      <Drawer open={Boolean(selected && !desktopInspector && mobileInspectorOpen)} onClose={closeContext} ariaLabel={t("conversations.aboutClient")} size="custom" className="max-w-[340px]">
        {customerContext}
      </Drawer>
      <Dialog open={automationOpen} onClose={() => setAutomationOpen(false)} title={t("conversations.crmAutomation")} size="md">
        {selectedInsight?.summary ? <p className="mb-4 text-sm text-platforma-text">{selectedInsight.summary}</p> : null}
        {qualifyMutation.isError ? <ErrorState error={qualifyMutation.error} /> : null}
        <div className="flex flex-wrap gap-2">
          <Button variant="ai" onClick={previewSelectedPipeline} disabled={!canSuggestAiPipeline} isLoading={qualifyMutation.isPending}>{t("conversations.previewQualification")}</Button>
          <Button variant="secondary" onClick={() => { setAutomationOpen(false); runSelectedPipeline(); }} disabled={!canApplyPipeline} isLoading={runPipelineMutation.isPending}>{t("conversations.confirmPipelineTitle")}</Button>
        </div>
      </Dialog>
      <Dialog open={addLinkOpen} onClose={() => setAddLinkOpen(false)} title={t("conversations.addLink")} size="sm">
        {createLeadMutation.error || createDealMutation.error ? <ErrorState error={createLeadMutation.error || createDealMutation.error} /> : null}
        <div className="space-y-3">{(["lead", "deal"] as const).filter(kind => context.data?.[kind].state === "empty").map(kind => <div key={kind} className="flex flex-wrap gap-2">
          {context.data?.actions[`link_${kind}`] ? <Button variant="secondary" onClick={() => { setAddLinkOpen(false); openCrmLinkModal(kind); }}>{t(kind === "lead" ? "conversations.linkLeadTitle" : "conversations.linkDealTitle")}</Button> : null}
          {context.data?.actions[`create_${kind}`] ? <Button variant="ghost" onClick={kind === "lead" ? createLinkedLead : createLinkedDeal} isLoading={kind === "lead" ? createLeadMutation.isPending : createDealMutation.isPending}>{t(kind === "lead" ? "conversations.createLead" : "conversations.createDeal")}</Button> : null}
        </div>)}</div>
      </Dialog>

      {pipelineReview ? <PipelineConfirmationDialog key={`${pipelineReview.conversationId}:${pipelineReview.previewId}`}
        review={pipelineReview} allowedActions={pipelineAllowedActions} pending={runPipelineMutation.isPending}
        error={runPipelineMutation.error ? (getApiFieldErrors(runPipelineMutation.error).preview_id
          ? t("conversations.pipelinePreviewExpired") : getApiErrorMessage(runPipelineMutation.error)) : null}
        onClose={() => setPipelineReview(null)} onConfirm={(confirmation) => runPipelineMutation.mutate(confirmation)} /> : null}

      <Dialog
        title={t("conversations.quickRepliesTitle")}
        open={quickRepliesOpen}
        onClose={() => setQuickRepliesOpen(false)}
        size="md"
        bodyClassName="bg-platforma-card p-0"
      >
        <div className="border-b border-platforma-border p-4">
          <input
            type="search"
            className="h-11 w-full rounded-control border border-platforma-border bg-platforma-card px-3 text-sm font-semibold text-platforma-text outline-hidden transition placeholder:text-platforma-muted focus:border-brand-400 focus:ring-4 focus:ring-brand-100"
            placeholder={t("conversations.quickRepliesSearch")}
            value={quickReplySearch}
            onChange={(event) => setQuickReplySearch(event.target.value)}
            autoFocus
          />
        </div>
        <div className="max-h-[56vh] overflow-y-auto p-3">
          {quickReplies.isError ? <ErrorState error={quickReplies.error} action={<Button variant="secondary" onClick={() => void quickReplies.refetch()}>{t("common.retry")}</Button>} /> : null}
          {quickReplies.isLoading ? (
            <LoadingState />
          ) : null}
          {!quickReplies.isLoading && !quickReplies.isError && !quickReplyTemplates.length ? (
            <EmptyState
              title={t("conversations.noTemplates")}
              description={t("conversations.noQuickRepliesText")}
            />
          ) : null}
          <div className="space-y-2">
            {quickReplyTemplates.map((template) => (
              <button
                key={template.id}
                type="button"
                className="w-full rounded-card border border-platforma-border bg-platforma-card p-3 text-left transition hover:border-brand-200 hover:bg-brand-50/40"
                onClick={() => insertQuickReply(template.text)}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-bold text-platforma-text">
                      {template.title}
                    </p>
                    <p className="mt-1 line-clamp-3 text-sm font-semibold leading-6 text-platforma-muted">
                      {template.text}
                    </p>
                  </div>
                  <span className="shrink-0 rounded-full bg-surface-muted px-2 py-1 text-[11px] font-bold text-platforma-muted">
                    {template.channel === "all"
                      ? t("conversations.allChannels")
                      : channelLabel(template.channel, t)}
                  </span>
                </div>
                {template.category ? (
                  <p className="mt-2 text-xs font-bold uppercase tracking-[0.12em] text-platforma-muted">
                    {template.category}
                  </p>
                ) : null}
              </button>
            ))}
          </div>
        </div>
      </Dialog>

      <Dialog
        title={
          crmLinkModal === "client"
            ? t("conversations.linkClientTitle")
            : crmLinkModal === "lead"
              ? t("conversations.linkLeadTitle")
              : t("conversations.linkDealTitle")
        }
        open={Boolean(crmLinkModal)}
        onClose={() => setCrmLinkModal(null)}
        size="md"
        bodyClassName="bg-platforma-card p-0"
      >
        <div className="border-b border-platforma-border p-4">
          <Input
            value={crmLinkSearch}
            onChange={(event) => setCrmLinkSearch(event.target.value)}
            placeholder={t("conversations.linkSearchPlaceholder")}
            autoFocus
          />
        </div>
        <div className="max-h-[56vh] overflow-y-auto p-3">
          {linkCandidates.isLoading ? <LoadingState /> : null}
          {linkCandidates.isError ? <ErrorState error={linkCandidates.error} action={<Button variant="secondary" onClick={() => void linkCandidates.refetch()} isLoading={linkCandidates.isFetching}>{t("common.retry")}</Button>} /> : null}
          {!linkCandidates.isLoading && !linkCandidates.isError && !linkCandidates.data?.length && crmLinkModal && context.data?.actions[`link_${crmLinkModal}`] ? <EmptyState title={t("conversations.noLinkCandidates")} description={t("conversations.noLinkCandidatesText")} /> : null}
          <div className="space-y-2">{(linkCandidates.data || []).map(candidate => <Button key={candidate.id} variant="ghost" className="w-full justify-start text-left" disabled={linkClientMutation.isPending || linkLeadMutation.isPending || linkDealMutation.isPending} onClick={() => {
            if (crmLinkModal === "client") linkClientToConversation(candidate.id);
            if (crmLinkModal === "lead") linkLeadToConversation(candidate.id);
            if (crmLinkModal === "deal") linkDealToConversation(candidate.id);
          }}><span className="min-w-0"><span className="block break-words">{candidate.title || `#${candidate.id}`}</span>{crmLinkModal === "client" ? <span className="block text-xs text-platforma-muted">{candidate.detail}</span> : <StatusBadge status={candidate.detail} size="sm" />}</span></Button>)}</div>
          {crmLinkModal === "client" && context.data?.actions.create_client ? <Button variant="secondary" className="mt-3" onClick={() => selected && createClientMutation.mutate({ conversationId: selected.id })} isLoading={createClientMutation.isPending}>{t("conversations.createClient")}</Button> : null}
          {linkClientMutation.error || linkLeadMutation.error || linkDealMutation.error || createClientMutation.error ? <ErrorState error={linkClientMutation.error || linkLeadMutation.error || linkDealMutation.error || createClientMutation.error} /> : null}
        </div>
      </Dialog>

      <Dialog
        title={t("conversations.createTaskTitle")}
        open={taskModalOpen}
        onClose={() => setTaskModalOpen(false)}
        size="md"
        bodyClassName="space-y-4 bg-platforma-card"
      >
        <Input
          label={t("tasks.title")}
          value={taskDraft.title}
          onChange={(event) =>
            setTaskDraft((current) => ({
              ...current,
              title: event.target.value,
            }))
          }
          placeholder={t("tasks.titlePlaceholder")}
          autoFocus
        />
        <Textarea
          label={t("tasks.description")}
          value={taskDraft.description}
          onChange={(event) =>
            setTaskDraft((current) => ({
              ...current,
              description: event.target.value,
            }))
          }
          placeholder={t("tasks.descriptionPlaceholder")}
          rows={4}
        />
        <div className="grid gap-3 sm:grid-cols-2">
          <Select
            label={t("tasks.priority")}
            value={taskDraft.priority}
            options={[
              { value: "low", label: t("tasks.priorityLow") },
              { value: "normal", label: t("tasks.priorityNormal") },
              { value: "high", label: t("tasks.priorityHigh") },
              { value: "urgent", label: t("tasks.priorityUrgent") },
            ]}
            onChange={(event) =>
              setTaskDraft((current) => ({
                ...current,
                priority: event.target.value as typeof taskDraft.priority,
              }))
            }
          />
          <Input
            label={t("tasks.dueAt")}
            type="datetime-local"
            value={taskDraft.due_at}
            onChange={(event) =>
              setTaskDraft((current) => ({
                ...current,
                due_at: event.target.value,
              }))
            }
          />
        </div>
        <div className="flex justify-end gap-2 border-t border-platforma-border pt-4">
          <Button
            type="button"
            variant="secondary"
            onClick={() => setTaskModalOpen(false)}
          >
            {t("common.cancel")}
          </Button>
          <Button
            type="button"
            onClick={submitTaskFromInspector}
            disabled={!taskDraft.title.trim()}
            isLoading={createTaskMutation.isPending}
          >
            {t("tasks.create")}
          </Button>
        </div>
      </Dialog>
    </div>
  );
}

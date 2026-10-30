import { useInboxLinking } from "./useInboxLinking";
import { InboxTaskDialog } from "./InboxTaskDialog";
import { InboxQuickRepliesDialog } from "./InboxQuickRepliesDialog";
import { useInboxQueries } from "./useInboxQueries";
import { useInboxFilterOptions } from "./useInboxFilterOptions";
import { useInboxSending } from "./useInboxSending";
import { createIdempotencyKey } from "./inboxIdempotency";
import { InfiniteData, useMutation, useQueryClient } from "@tanstack/react-query";
import { BellDot, CheckSquare, Link2, PauseCircle, Sparkles, UserRound, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Navigate, Link, useNavigate, useParams, useSearchParams } from "react-router";

import { getApiErrorMessage, getApiFieldErrors } from "../../api/client";

import { inboxApi, inboxQueryKeys, type InboxConversation, type InboxFilters, type InboxMessage, type PaginatedInboxMessageResponse, type PipelineAction, type PipelineConfirmation } from "../../api/inbox";
import { ClientLinkConfirmation } from "./components/ClientLinkConfirmation";
import { useActionFeedback } from "../../components/actions/useActionFeedback";
import { usePageHeader } from "../../components/layout/PageHeaderContext";
import { WorkQueueLayout } from "../../components/layout/WorkQueueLayout";
import { useNotification } from "../../components/notifications/NotificationProvider";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Dialog, Drawer } from "../../components/ui/Overlay";

import { StatusBadge } from "../../components/ui/StatusBadge";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/StateViews";

import { cn } from "../../lib/cn";
import { useI18n } from "../../lib/i18n";
import { hasPermission } from "../../lib/permissions";

import { useActiveBusiness } from "../../hooks/useBusiness";
import { useAuth } from "../auth/AuthProvider";
import { ConversationListPane } from "./components/ConversationListPane";
import type { ActionMenuItem } from "../../components/ui/ActionMenu";
import { useMediaQuery } from "../../hooks/useMediaQuery";
import { InboxCustomerContext } from "./components/InboxCustomerContext";
import { appendReplyDraft, useInboxDraft } from "./hooks/useInboxDraft";
import { ConversationThreadPane } from "./components/ConversationThreadPane";
import { Tooltip } from "./components/ConversationPrimitives";
import { MessageDeliveryDetails } from "./components/MessageDeliveryDetails";
import { PipelineConfirmationDialog, type PipelineReview } from "./components/PipelineConfirmationDialog";
import { channelOptions, priorityOptions } from "./conversationConstants";
import { conversationTitle, getAutoPipelineInsight } from "./conversationUtils";
import { useConversationFilters } from "./hooks/useConversationFilters";
import { taskDateISO } from "../tasks/workspaceUtils";

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
  const desktopInspector = useMediaQuery("(min-width: 1440px)");
  const desktopThread = useMediaQuery("(min-width: 1024px)");
  const readSelectionRef = useRef<string | null>(null);
  const contextTriggerRef = useRef<HTMLButtonElement>(null);
  const aiTriggerRef = useRef<HTMLButtonElement>(null);

  const [suggestedReply, setSuggestedReply] = useState("");

  const [quickRepliesOpen, setQuickRepliesOpen] = useState(false);
  const [pipelineReview, setPipelineReview] = useState<PipelineReview | null>(
    null,
  );
  const [quickReplySearch, setQuickReplySearch] = useState("");

  const [taskModalOpen, setTaskModalOpen] = useState(false);
  const taskIdempotencyRef = useRef<{ signature: string; key: string } | null>(
    null,
  );
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
    const maxHeight = Math.min(
      window.matchMedia("(max-width: 640px)").matches ? 110 : 132,
      Math.max(
        44,
        (window.visualViewport?.height ?? window.innerHeight) * 0.25,
      ),
    );
    composer.style.height = "auto";
    composer.style.height = `${Math.max(44, Math.min(composer.scrollHeight, maxHeight))}px`;
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

  const {
    summary,
    communicationConnectors,
    conversations,
    bots,
    items,
    sortedItems,
    selectedConversation,
    selected,
    context,
    quickReplies,
    messages,
    messageList,
  } = useInboxQueries({
    businessId,
    canViewIntegrations,
    normalizedFilters,
    sortBy,
    selectedId,
    userId: user?.id,
  });

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
  const { draft, draftKey, setDraft, clearSentDraft } = useInboxDraft(
    user?.id,
    selected?.business,
    selected?.id,
  );
  const currentConversationRef = useRef(selected?.id);
  currentConversationRef.current = selected?.id;

  const canUpdate =
    context.data?.actions.update ??
    hasPermission(user, selected?.business, "conversations", "update");
  useEffect(() => {
    setSuggestedReply("");
    setMobileInspectorOpen(false);
    setCrmLinkModal(null);
    setClientLinkPreview(null);
    setAddLinkOpen(false);
    setAutomationOpen(false);
    setPipelineReview(null);
    setTaskModalOpen(false);
    taskIdempotencyRef.current = null;
    setQuickRepliesOpen(false);
  }, [user?.id, selected?.business, selected?.id]);

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
    const priority = slaOverdue || handoff || unread || sortedItems[0];
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

  const {
    hasActiveFilters,
    activeFilterSummary,
    queueFilterOptions,
    ownerFilterOptions,
    agentFilterOptions,
    localizedChannelOptions,
    localizedPriorityOptions,
    quickReplyTemplates,
    localizedSortOptions,
    localizedStatusOptions,
  } = useInboxFilterOptions({
    items,
    conversations,
    summary,
    bots,
    quickReplies,
    filters,
    quickReplySearch,
    t,
  });

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
    if (
      id === selected?.id &&
      context.data?.actions.update &&
      (conversation?.unread_count || 0) > 0
    ) {
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
  }, [
    selected,
    user?.id,
    desktopThread,
    mobileThreadOpen,
    messages.isSuccess,
    context.data?.actions.update,
    markReadMutation.mutate,
  ]);

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

  const { retryMessage, sendMutation, retryMessageMutation, sendReply } =
    useInboxSending({
      selected,
      draft,
      draftKey,
      canUpdate,
      clearSentDraft,
      currentConversationRef,
      setSuggestedReply,
      setNotice,
      t,
      invalidateInbox,
      notifyError,
      composerRef,
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

  const {clientLinkPreview, setClientLinkPreview, clientLinkRefreshed, setClientLinkRefreshed, crmLinkModal, setCrmLinkModal, crmLinkSearch, setCrmLinkSearch, linkCandidates, linkClientMutation, linkLeadMutation, linkDealMutation, linkClientToConversation, linkLeadToConversation, linkDealToConversation} = useInboxLinking({user, selected, context, currentConversationRef, setPipelineReview, t, setNotice, invalidateInbox, notifyError});

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

  const createTaskMutation = useMutation({
    mutationFn: ({ timezone, ...payload }: Parameters<typeof inboxApi.createTask>[0] & { timezone: string }) =>
      inboxApi.createTask({ ...payload, due_at: taskDateISO(payload.due_at || "", timezone) }),
    onSuccess: async () => {
      taskIdempotencyRef.current = null;
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
    (action) =>
      action.code !== "connect_channel" &&
      (canViewIntegrations || !isIntegrationsAction(action.href)),
  );
  const channelAgent = (bots.data || []).find(
    (bot) => bot.business === businessId && bot.scenario !== "crm",
  );
  const connectChannelAction =
    canViewIntegrations &&
    hasPermission(user, businessId, "ai_automation", "view") ? (
      <Link
        to={
          channelAgent
            ? `/app/ai-agents/${channelAgent.id}/channels`
            : "/app/ai-agents"
        }
        className="platforma-focus-ring inline-flex min-h-10 items-center justify-center rounded-control bg-brand-500 px-4 py-2 text-sm font-bold text-white shadow-xs transition hover:bg-brand-600"
      >
        {t("conversations.nextAction.connect_channel")}
      </Link>
    ) : undefined;

  function insertQuickReply(text: string) {
    setDraft((current) => appendReplyDraft(current, text));
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
    taskIdempotencyRef.current = null;
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
    if (!selected || createTaskMutation.isPending) return;
    const payload = {
      conversationId: selected.id,
      title: taskDraft.title,
      description: taskDraft.description,
      priority: taskDraft.priority,
      due_at: taskDraft.due_at,
      timezone: context.data?.timezone || business?.timezone || "UTC",
    };
    const signature = JSON.stringify([user?.id, selected.business, payload]);
    const previous = taskIdempotencyRef.current;
    const idempotencyKey =
      previous?.signature === signature
        ? previous.key
        : createIdempotencyKey(`inbox:task:${selected.id}`);
    taskIdempotencyRef.current = { signature, key: idempotencyKey };
    createTaskMutation.mutate({ ...payload, idempotencyKey });
  }

  function openCrmLinkModal(target: "client" | "lead" | "deal") {
    linkClientMutation.reset();
    setClientLinkPreview(null);
    setClientLinkRefreshed(false);
    linkLeadMutation.reset();
    linkDealMutation.reset();
    createClientMutation.reset();
    setCrmLinkSearch("");
    setCrmLinkModal(target);
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
  const pipelineAllowedActions: PipelineAction[] = (
    [
      ["create_lead", "leads"],
      ["create_task", "tasks"],
      ["create_deal", "deals"],
    ] as const
  )
    .filter(([, resource]) =>
      hasPermission(user, selected?.business, resource, "create"),
    )
    .map(([action]) => action);

  const canLoadMoreMessages = Boolean(messages.hasNextPage);
  const lastMessage = messageList[messageList.length - 1];
  const lastCustomerMessage = [...messageList]
    .reverse()
    .find(
      (message) =>
        message.direction === "inbound" &&
        message.sender_type !== "system" &&
        message.text?.trim(),
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

  useEffect(() => {
    const onResize = () => resizeComposer();
    window.addEventListener("resize", onResize);
    window.visualViewport?.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      window.visualViewport?.removeEventListener("resize", onResize);
    };
  }, []);

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
          error={pageError}
          message={getApiErrorMessage(pageError)}
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
    if (desktopInspector) {
      setInspectorOpen(false);
      contextTriggerRef.current?.focus();
    }
  }
  const contextMenu: ActionMenuItem[] = (["client", "lead", "deal"] as const)
    .filter(
      (kind) =>
        context.data?.[kind].state === "available" &&
        context.data.actions[`link_${kind}`],
    )
    .map((kind) => ({
      key: kind,
      label: t(`conversations.changeLink.${kind}`),
      icon: Link2,
      onSelect: () => openCrmLinkModal(kind),
    }));
  const threadMenu: ActionMenuItem[] = [
    ...(canUpdate && selected?.status === "open" && selected.bot_enabled
      ? [
          {
            key: "handoff",
            label: t("conversations.handoffToManager"),
            icon: UserRound,
            disabled: handoffMutation.isPending,
            onSelect: () =>
              handoffMutation.mutate({
                conversationId: selected.id,
                reason: "",
              }),
          },
        ]
      : []),
    ...(canUpdate &&
    canSuggestAi &&
    selected?.status === "open" &&
    selected.handoff_resume_started_at
      ? [
          {
            key: "keep-ai-paused",
            label: t("conversations.keepAiPaused"),
            icon: PauseCircle,
            disabled: toggleBotMutation.isPending,
            onSelect: () =>
              toggleBotMutation.mutate({
                conversationId: selected.id,
                botEnabled: false,
              }),
          },
        ]
      : []),
    ...(canUpdate
      ? [
          {
            key: "unread",
            label: t("conversations.markUnreadAction"),
            icon: BellDot,
            onSelect: () => selected && markUnreadMutation.mutate(selected.id),
          },
          ...localizedPriorityOptions.map((option) => ({
            key: `priority-${option.value}`,
            label: `${t("conversations.priority")}: ${option.label}`,
            icon: BellDot,
            disabled:
              setPriorityMutation.isPending ||
              selected?.priority === option.value,
            onSelect: () =>
              selected &&
              setPriorityMutation.mutate({
                conversationId: selected.id,
                priority: option.value as NonNullable<
                  InboxConversation["priority"]
                >,
              }),
          })),
        ]
      : []),
    ...(context.data?.actions.create_task
      ? [
          {
            key: "task",
            label: t("conversations.createTask"),
            icon: CheckSquare,
            onSelect: createLinkedTask,
          },
        ]
      : []),
    ...(canSuggestAiPipeline || canRunAiPipeline
      ? [
          {
            key: "automation",
            label: t("conversations.crmAutomation"),
            icon: Sparkles,
            onSelect: () => setAutomationOpen(true),
          },
        ]
      : []),
  ];
  const customerContext = (
    <InboxCustomerContext
      data={context.data}
      loading={context.isLoading}
      error={context.error}
      retrying={context.isFetching}
      menuItems={contextMenu}
      inDrawer={!desktopInspector}
      onRetry={() => void context.refetch()}
      onClose={closeContext}
      onNavigate={(href) => {
        setMobileInspectorOpen(false);
        navigate(href);
      }}
      onLinkClient={() => openCrmLinkModal("client")}
      onAddLink={() => setAddLinkOpen(true)}
    />
  );

  return (
    <div
      data-testid="inbox-workspace-ready"
      className="h-[calc(100dvh-var(--app-header-height)-var(--inbox-mobile-nav))] overflow-hidden"
    >
      <WorkQueueLayout
        edgeToEdge
        className={cn(
          "lg:grid-cols-[288px_minmax(0,1fr)]",
          inspectorOpen
            ? "min-[90rem]:grid-cols-[288px_minmax(0,1fr)_320px]"
            : "min-[90rem]:grid-cols-[288px_minmax(0,1fr)]",
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
          threadMenu={threadMenu}
          headerActions={
            <Button
              ref={contextTriggerRef}
              variant="ghost"
              size="icon"
              className="h-11 w-11 shrink-0 lg:h-10 lg:w-10"
              title={t("conversations.aboutClient")}
              aria-label={t("conversations.aboutClient")}
              onClick={() =>
                desktopInspector
                  ? setInspectorOpen((state) => !state)
                  : setMobileInspectorOpen(true)
              }
              aria-expanded={
                desktopInspector ? inspectorOpen : mobileInspectorOpen
              }
            >
              <UserRound size={18} />
            </Button>
          }
          aiActions={
            canSuggestAi ? (
              <Tooltip label={t("conversations.prepareReply")} side="top">
                <Button
                  ref={aiTriggerRef}
                  variant="ghost"
                  size="icon"
                  className="h-11 w-11 shrink-0"
                  aria-label={t("conversations.prepareReply")}
                  aria-busy={suggestMutation.isPending}
                  onClick={() =>
                    selected && suggestMutation.mutate(selected.id)
                  }
                  disabled={
                    !canUpdate ||
                    selected?.status !== "open" ||
                    suggestMutation.isPending
                  }
                >
                  <Sparkles
                    size={18}
                    className={
                      suggestMutation.isPending ? "animate-pulse" : undefined
                    }
                  />
                </Button>
              </Tooltip>
            ) : null
          }
          aiPreview={
            suggestedReply ||
            (suggestMutation.isError &&
              suggestMutation.variables === selected?.id) ? (
              <div
                data-testid="inbox-ai-preview"
                className="mb-3 rounded-card border border-platforma-border bg-surface-muted p-3"
              >
                {suggestMutation.isError &&
                suggestMutation.variables === selected?.id ? (
                  <p role="alert" className="text-xs text-platforma-danger">
                    {getApiErrorMessage(suggestMutation.error)}
                  </p>
                ) : null}
                {suggestedReply ? (
                  <>
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <Button
                        variant="secondary"
                        size="sm"
                        disabled={!canUpdate || selected?.status !== "open"}
                        onClick={() => {
                          insertQuickReply(suggestedReply);
                          setSuggestedReply("");
                        }}
                      >
                        {t("conversations.useSuggestedReply")}
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-11 w-11"
                        aria-label={t("common.close")}
                        onClick={() => {
                          setSuggestedReply("");
                          aiTriggerRef.current?.focus();
                        }}
                      >
                        <X size={16} />
                      </Button>
                    </div>
                    <p className="max-h-[min(132px,20dvh)] overflow-y-auto whitespace-pre-wrap break-words text-sm leading-[22px] text-platforma-text">
                      {suggestedReply}
                    </p>
                  </>
                ) : null}
              </div>
            ) : null
          }
          renderDelivery={(message) => (
            <MessageDeliveryDetails
              message={message}
              canRetry={canUpdate}
              retryPending={
                retryMessageMutation.isPending &&
                retryMessageMutation.variables?.messageId === message.id
              }
              onRetry={() => retryMessage(message.id)}
              t={t}
            />
          )}
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
          canToggleBot={
            canSuggestAi &&
            hasPermission(user, selected?.business, "conversations", "update")
          }
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

        <aside
          className={cn(
            "hidden min-h-0 flex-col border-l border-platforma-border min-[90rem]:flex",
            !inspectorOpen && "min-[90rem]:hidden",
          )}
        >
          {selected ? (
            customerContext
          ) : (
            <div className="grid flex-1 place-items-center bg-surface-muted p-3 text-center text-sm font-bold text-platforma-muted">
              {t("conversations.selectContext")}
            </div>
          )}
        </aside>
      </WorkQueueLayout>

      <Drawer
        open={Boolean(selected && !desktopInspector && mobileInspectorOpen)}
        onClose={closeContext}
        ariaLabel={t("conversations.aboutClient")}
        size="custom"
        className="max-w-[340px]"
      >
        {customerContext}
      </Drawer>
      <Dialog
        open={automationOpen}
        onClose={() => setAutomationOpen(false)}
        title={t("conversations.crmAutomation")}
        size="md"
      >
        {selectedInsight?.summary ? (
          <p className="mb-4 text-sm text-platforma-text">
            {selectedInsight.summary}
          </p>
        ) : null}
        {qualifyMutation.isError ? (
          <ErrorState error={qualifyMutation.error} />
        ) : null}
        <div className="flex flex-wrap gap-2">
          <Button
            variant="ai"
            onClick={previewSelectedPipeline}
            disabled={!canSuggestAiPipeline}
            isLoading={qualifyMutation.isPending}
          >
            {t("conversations.previewQualification")}
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              setAutomationOpen(false);
              runSelectedPipeline();
            }}
            disabled={!canApplyPipeline}
            isLoading={runPipelineMutation.isPending}
          >
            {t("conversations.confirmPipelineTitle")}
          </Button>
        </div>
      </Dialog>
      <Dialog
        open={addLinkOpen}
        onClose={() => setAddLinkOpen(false)}
        title={t("conversations.addLink")}
        size="sm"
      >
        {createLeadMutation.error || createDealMutation.error ? (
          <ErrorState
            error={createLeadMutation.error || createDealMutation.error}
          />
        ) : null}
        <div className="space-y-3">
          {(["lead", "deal"] as const)
            .filter((kind) => context.data?.[kind].state === "empty")
            .map((kind) => (
              <div key={kind} className="flex flex-wrap gap-2">
                {context.data?.actions[`link_${kind}`] ? (
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setAddLinkOpen(false);
                      openCrmLinkModal(kind);
                    }}
                  >
                    {t(
                      kind === "lead"
                        ? "conversations.linkLeadTitle"
                        : "conversations.linkDealTitle",
                    )}
                  </Button>
                ) : null}
                {context.data?.actions[`create_${kind}`] ? (
                  <Button
                    variant="ghost"
                    onClick={
                      kind === "lead" ? createLinkedLead : createLinkedDeal
                    }
                    isLoading={
                      kind === "lead"
                        ? createLeadMutation.isPending
                        : createDealMutation.isPending
                    }
                  >
                    {t(
                      kind === "lead"
                        ? "conversations.createLead"
                        : "conversations.createDeal",
                    )}
                  </Button>
                ) : null}
              </div>
            ))}
        </div>
      </Dialog>

      {pipelineReview ? (
        <PipelineConfirmationDialog
          key={`${pipelineReview.conversationId}:${pipelineReview.previewId}`}
          review={pipelineReview}
          allowedActions={pipelineAllowedActions}
          pending={runPipelineMutation.isPending}
          error={
            runPipelineMutation.error
              ? getApiFieldErrors(runPipelineMutation.error).preview_id
                ? t("conversations.pipelinePreviewExpired")
                : getApiErrorMessage(runPipelineMutation.error)
              : null
          }
          onClose={() => setPipelineReview(null)}
          onConfirm={(confirmation) => runPipelineMutation.mutate(confirmation)}
        />
      ) : null}

      <InboxQuickRepliesDialog
        t={t}
        quickRepliesOpen={quickRepliesOpen}
        setQuickRepliesOpen={setQuickRepliesOpen}
        quickReplySearch={quickReplySearch}
        setQuickReplySearch={setQuickReplySearch}
        quickReplies={quickReplies}
        quickReplyTemplates={quickReplyTemplates}
        selected={selected}
        businessId={businessId}
        user={user}
        insertQuickReply={insertQuickReply}
      />

      <Dialog
        title={
          clientLinkPreview
            ? t("conversations.clientReplacement.title")
            : crmLinkModal === "client"
              ? t("conversations.linkClientTitle")
              : crmLinkModal === "lead"
                ? t("conversations.linkLeadTitle")
                : t("conversations.linkDealTitle")
        }
        open={Boolean(crmLinkModal)}
        onClose={() => {
          if (!linkClientMutation.isPending) {
            setCrmLinkModal(null);
            setClientLinkPreview(null);
          }
        }}
        size="md"
        bodyClassName="bg-platforma-card p-0"
      >
        {clientLinkPreview ? (
          <ClientLinkConfirmation
            preview={clientLinkPreview}
            refreshed={clientLinkRefreshed}
            pending={linkClientMutation.isPending}
            error={linkClientMutation.error}
            onCancel={() => {
              setClientLinkPreview(null);
              linkClientMutation.reset();
            }}
            onConfirm={() =>
              selected &&
              linkClientMutation.mutate({
                conversationId: selected.id,
                clientId: clientLinkPreview.next_client.id,
                confirmationToken: clientLinkPreview.confirmation_token,
              })
            }
          />
        ) : (
          <>
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
              {linkCandidates.isError ? (
                <ErrorState
                  error={linkCandidates.error}
                  action={
                    <Button
                      variant="secondary"
                      onClick={() => void linkCandidates.refetch()}
                      isLoading={linkCandidates.isFetching}
                    >
                      {t("common.retry")}
                    </Button>
                  }
                />
              ) : null}
              {!linkCandidates.isLoading &&
              !linkCandidates.isError &&
              !linkCandidates.data?.length &&
              crmLinkModal &&
              context.data?.actions[`link_${crmLinkModal}`] ? (
                <EmptyState
                  title={t("conversations.noLinkCandidates")}
                  description={t("conversations.noLinkCandidatesText")}
                />
              ) : null}
              <div className="space-y-2">
                {(linkCandidates.data || []).map((candidate) => (
                  <Button
                    key={candidate.id}
                    variant="ghost"
                    className="w-full justify-start text-left"
                    disabled={
                      linkClientMutation.isPending ||
                      linkLeadMutation.isPending ||
                      linkDealMutation.isPending
                    }
                    onClick={() => {
                      if (crmLinkModal === "client")
                        linkClientToConversation(candidate.id);
                      if (crmLinkModal === "lead")
                        linkLeadToConversation(candidate.id);
                      if (crmLinkModal === "deal")
                        linkDealToConversation(candidate.id);
                    }}
                  >
                    <span className="min-w-0">
                      <span className="block break-words">
                        {candidate.title || `#${candidate.id}`}
                      </span>
                      {crmLinkModal === "client" ? (
                        <span className="block text-xs text-platforma-muted">
                          {candidate.detail}
                        </span>
                      ) : (
                        <StatusBadge status={candidate.detail} size="sm" />
                      )}
                    </span>
                  </Button>
                ))}
              </div>
              {crmLinkModal === "client" &&
              context.data?.actions.create_client ? (
                <Button
                  variant="secondary"
                  className="mt-3"
                  onClick={() =>
                    selected &&
                    createClientMutation.mutate({ conversationId: selected.id })
                  }
                  isLoading={createClientMutation.isPending}
                >
                  {t("conversations.createClient")}
                </Button>
              ) : null}
              {linkClientMutation.error ||
              linkLeadMutation.error ||
              linkDealMutation.error ||
              createClientMutation.error ? (
                <ErrorState
                  error={
                    linkClientMutation.error ||
                    linkLeadMutation.error ||
                    linkDealMutation.error ||
                    createClientMutation.error
                  }
                />
              ) : null}
            </div>
          </>
        )}
      </Dialog>

      <InboxTaskDialog
        t={t}
        taskModalOpen={taskModalOpen}
        setTaskModalOpen={setTaskModalOpen}
        taskDraft={taskDraft}
        setTaskDraft={setTaskDraft}
        submitTaskFromInspector={submitTaskFromInspector}
        createTaskMutation={createTaskMutation}
      />
    </div>
  );
}

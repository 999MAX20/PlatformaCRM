import { useMutation } from "@tanstack/react-query";

import { useRef } from "react";

import { inboxApi, type InboxConversation } from "../../api/inbox";

import { useActionFeedback } from "../../components/actions/useActionFeedback";

import { useInboxDraft } from "./hooks/useInboxDraft";

import type { Dispatch, SetStateAction, RefObject } from "react";
import type { Translate } from "./conversationTypes";
import { createIdempotencyKey } from "./inboxIdempotency";
type Args = {
  selected: InboxConversation | null;
  draft: string;
  draftKey: string | null;
  canUpdate: boolean;
  clearSentDraft: ReturnType<typeof useInboxDraft>["clearSentDraft"];
  currentConversationRef: RefObject<number | undefined>;
  setSuggestedReply: Dispatch<SetStateAction<string>>;
  setNotice: (
    message: string | null,
    tone?: "success" | "info" | "warning" | "danger",
  ) => void;
  t: Translate;
  invalidateInbox: () => Promise<void>;
  notifyError: ReturnType<typeof useActionFeedback>["notifyError"];
  composerRef: RefObject<HTMLTextAreaElement | null>;
};
export function useInboxSending({
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
}: Args) {
  const retryKeys = useRef(new Map<number, string>());
  const sendIdempotencyRef = useRef<{
    conversationId: number;
    text: string;
    key: string;
  } | null>(null);
  const sendMutation = useMutation({
    mutationFn: (
      payload: Parameters<typeof inboxApi.sendMessage>[0] & {
        draftKey: string | null;
      },
    ) => inboxApi.sendMessage(payload),
    onSuccess: async (result, variables) => {
      sendIdempotencyRef.current = null;
      clearSentDraft(variables.draftKey, variables.text);
      if (currentConversationRef.current === Number(variables.conversationId))
        setSuggestedReply("");
      const noticeKey =
        result.status === "sent"
          ? "conversations.replySent"
          : result.status === "accepted"
            ? "conversations.deliveryYCloudAccepted"
            : result.status === "delivery_unknown"
              ? "conversations.deliveryYCloudUnknown"
              : result.status === "failed"
                ? "conversations.deliveryStatusFailed"
                : "conversations.deliveryStatusQueued";
      setNotice(
        t(noticeKey),
        result.status === "failed" || result.status === "delivery_unknown"
          ? "warning"
          : "success",
      );
      await invalidateInbox();
    },
    onError: (error) => notifyError(error, { focusTarget: composerRef }),
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
  function sendReply() {
    const text = draft.trim();
    if (
      !selected ||
      !text ||
      !canUpdate ||
      selected.status !== "open" ||
      sendMutation.isPending
    )
      return;
    const previousRequest = sendIdempotencyRef.current;
    const idempotencyKey =
      previousRequest?.conversationId === selected.id &&
      previousRequest.text === text
        ? previousRequest.key
        : createIdempotencyKey(`inbox:send:${selected.id}`);
    sendIdempotencyRef.current = {
      conversationId: selected.id,
      text,
      key: idempotencyKey,
    };
    sendMutation.mutate({
      conversationId: selected.id,
      text,
      idempotencyKey,
      draftKey,
    });
  }
  function retryMessage(messageId: number) {
    if (!selected || retryMessageMutation.isPending) return;
    let key = retryKeys.current.get(messageId);
    if (!key) {
      key = createIdempotencyKey(`inbox:retry:${messageId}`);
      retryKeys.current.set(messageId, key);
    }
    retryMessageMutation.mutate({
      conversationId: selected.id,
      messageId: messageId,
      idempotencyKey: key,
    });
  }
  return { sendMutation, retryMessageMutation, sendReply, retryMessage };
}

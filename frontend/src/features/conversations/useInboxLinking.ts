

import { useInboxQueries } from "./useInboxQueries";

import { useMutation, useQuery } from "@tanstack/react-query";

import { useState } from "react";

import { inboxApi, type InboxClientLinkPreview } from "../../api/inbox";

import { useActionFeedback } from "../../components/actions/useActionFeedback";

import { useI18n } from "../../lib/i18n";

import { useAuth } from "../auth/AuthProvider";

import { type PipelineReview } from "./components/PipelineConfirmationDialog";

import type { Dispatch, SetStateAction, RefObject } from "react";
type Args={user: ReturnType<typeof useAuth>["user"]; selected: ReturnType<typeof useInboxQueries>["selected"]; context: ReturnType<typeof useInboxQueries>["context"]; currentConversationRef: RefObject<number | undefined>; setPipelineReview: Dispatch<SetStateAction<PipelineReview | null>>; t: ReturnType<typeof useI18n>["t"]; setNotice: (message:string | null,tone?: "success" | "info" | "warning" | "danger") => void; invalidateInbox: () => Promise<void>; notifyError: ReturnType<typeof useActionFeedback>["notifyError"];};
export function useInboxLinking({user, selected, context, currentConversationRef, setPipelineReview, t, setNotice, invalidateInbox, notifyError}:Args){
const [clientLinkPreview, setClientLinkPreview] =
    useState<InboxClientLinkPreview | null>(null);
const [clientLinkRefreshed, setClientLinkRefreshed] = useState(false);
const [crmLinkModal, setCrmLinkModal] = useState<
    "client" | "lead" | "deal" | null
  >(null);
const [crmLinkSearch, setCrmLinkSearch] = useState("");
const linkCandidates = useQuery({
    queryKey: [
      "inbox-link-candidates",
      user?.id,
      selected?.business,
      selected?.id,
      crmLinkModal,
      crmLinkSearch,
    ],
    queryFn: () =>
      inboxApi.linkCandidates(selected!.id, crmLinkModal!, crmLinkSearch),
    enabled: Boolean(
      selected && crmLinkModal && context.data?.actions[`link_${crmLinkModal}`],
    ),
    retry: false,
  });
const linkClientMutation = useMutation({
    mutationFn: inboxApi.linkClient,
    onSuccess: async (result, variables) => {
      if (currentConversationRef.current !== variables.conversationId) return;
      if ("requires_confirmation" in result) {
        setClientLinkPreview(result);
        setClientLinkRefreshed(Boolean(variables.confirmationToken));
        return;
      }
      setClientLinkPreview(null);
      setPipelineReview(null);
      setNotice(t("conversations.clientLinkedShort"));
      setCrmLinkModal(null);
      await invalidateInbox();
    },
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
const linkDealMutation = useMutation({
    mutationFn: inboxApi.linkDeal,
    onSuccess: async () => {
      setNotice(t("conversations.dealLinkedShort"));
      setCrmLinkModal(null);
      await invalidateInbox();
    },
    onError: (error) => notifyError(error),
  });
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
return {clientLinkPreview, setClientLinkPreview, clientLinkRefreshed, setClientLinkRefreshed, crmLinkModal, setCrmLinkModal, crmLinkSearch, setCrmLinkSearch, linkCandidates, linkClientMutation, linkLeadMutation, linkDealMutation, linkClientToConversation, linkLeadToConversation, linkDealToConversation};
}
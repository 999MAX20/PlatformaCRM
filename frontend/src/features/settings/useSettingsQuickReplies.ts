import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { quickRepliesApi } from "../../api/quickReplies";

import { useActiveBusiness } from "../../hooks/useBusiness";
import { useI18n } from "../../lib/i18n";

import type { QuickReplyTemplate } from "../../types";

type Context = {
  business: ReturnType<typeof useActiveBusiness>["business"];
  canManageConversations: boolean;
  activeSettingsSection: string;
  queryClient: ReturnType<typeof useQueryClient>;
  t: ReturnType<typeof useI18n>["t"];
};

export function useSettingsQuickReplies({ business, canManageConversations, activeSettingsSection, queryClient, t }: Context) {
const [quickReplyForm, setQuickReplyForm] = useState({
    title: "",
    text: "",
    category: "",
    channel: "all",
  });

const [editingQuickReplyId, setEditingQuickReplyId] = useState<number | null>(
    null,
  );

const [quickReplyEditForm, setQuickReplyEditForm] = useState({
    title: "",
    text: "",
    category: "",
    channel: "all" as QuickReplyTemplate["channel"],
    is_active: true,
  });

const quickReplies = useQuery({
    queryKey: ["quick-replies", business?.id],
    queryFn: () => quickRepliesApi.listAll({ business: business?.id }),
    enabled: activeSettingsSection === "quick-replies" && Boolean(business && canManageConversations),
  });

const quickReplyMutation = useMutation({
    mutationFn: () => {
      if (!business) throw new Error("Business is required.");
      if (!canManageConversations)
        throw new Error(
          t("permissions.forbidden", {
            action: t("permissions.action.manage"),
            resource: t("permissions.resource.conversations"),
          }),
        );
      return quickRepliesApi.create({
        business: business.id,
        title: quickReplyForm.title,
        text: quickReplyForm.text,
        category: quickReplyForm.category,
        channel: quickReplyForm.channel as QuickReplyTemplate["channel"],
        sort_order: 0,
        is_active: true,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["quick-replies"] });
      setQuickReplyForm({ title: "", text: "", category: "", channel: "all" });
    },
  });

const updateQuickReplyMutation = useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: number;
      payload: Partial<QuickReplyTemplate>;
    }) => {
      if (!canManageConversations)
        throw new Error(
          t("permissions.forbidden", {
            action: t("permissions.action.manage"),
            resource: t("permissions.resource.conversations"),
          }),
        );
      return quickRepliesApi.update({
        id,
        payload,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["quick-replies"] });
      setEditingQuickReplyId(null);
    },
  });

const removeQuickReplyMutation = useMutation({
    mutationFn: (id: number) => {
      if (!canManageConversations)
        throw new Error(
          t("permissions.forbidden", {
            action: t("permissions.action.manage"),
            resource: t("permissions.resource.conversations"),
          }),
        );
      return quickRepliesApi.remove(id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["quick-replies"] });
      if (editingQuickReplyId) setEditingQuickReplyId(null);
    },
  });

function startEditingQuickReply(template: QuickReplyTemplate) {
    setEditingQuickReplyId(Number(template.id));
    setQuickReplyEditForm({
      title: template.title,
      text: template.text,
      category: template.category || "",
      channel: template.channel,
      is_active: template.is_active,
    });
  }

const quickReplyChannelOptions = [
    { value: "all", label: t("settings.channel.all") },
    { value: "website", label: t("settings.channel.website") },
    { value: "telegram", label: "Telegram" },
    { value: "whatsapp", label: "WhatsApp" },
    { value: "instagram", label: "Instagram" },
    { value: "manual", label: t("settings.channel.manual") },
  ];
return { quickReplyForm, setQuickReplyForm, editingQuickReplyId, setEditingQuickReplyId, quickReplyEditForm, setQuickReplyEditForm, quickReplies, quickReplyMutation, updateQuickReplyMutation, removeQuickReplyMutation, startEditingQuickReply, quickReplyChannelOptions };
}

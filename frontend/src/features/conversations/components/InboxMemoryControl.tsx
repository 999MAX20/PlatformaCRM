import { useMutation, useQueryClient } from "@tanstack/react-query";
import { inboxApi, type InboxConversation } from "../../../api/inbox";
import { RotateCcw, Sparkles } from "lucide-react";
import { ActionMenu, type ActionMenuItem } from "../../../components/ui/ActionMenu";
import { ErrorState } from "../../../components/ui/StateViews";
import { useActionConfirm } from "../../../components/actions/ActionConfirmProvider";
import { useI18n } from "../../../lib/i18n";
import { hasPermission } from "../../../lib/permissions";
import { useAuth } from "../../auth/AuthProvider";

export function InboxMemoryControl({ conversation, items }: { conversation: InboxConversation; items: ActionMenuItem[] }) {
  const { t } = useI18n();
  const { user } = useAuth();
  const confirm = useActionConfirm();
  const client = useQueryClient();
  const reset = useMutation({ mutationFn: () => inboxApi.resetAIMemory(conversation.id), onSuccess: async () => {
    await client.invalidateQueries({ queryKey: ["inbox-conversations"] });
  } });
  const canReset = hasPermission(user, conversation.business, "conversations", "update") && hasPermission(user, conversation.business, "ai_assistant", "suggest");
  const menuItems: ActionMenuItem[] = [...items];
  if (conversation.ai_safety) menuItems.push({ key: "ai-usage", label: t("customerSafety.usage", { used: conversation.ai_safety.calls_used, limit: conversation.ai_safety.calls_limit }), icon: Sparkles, disabled: true, onSelect: () => {} });
  if (canReset) menuItems.push({ key: "reset-memory", label: t("agentChat.reset"), icon: RotateCcw, disabled: reset.isPending, onSelect: async () => {
    const result = await confirm({ title: t("agentChat.reset"), description: t("agentChat.resetText"), confirmLabel: t("agentChat.reset"), tone: "neutral" });
    if (result.confirmed) reset.mutate();
  } });
  if (!menuItems.length) return null;
  return <div>
    <ActionMenu label={t("conversations.dialogActions")} items={menuItems} />
    {reset.error && <ErrorState error={reset.error} />}
    {reset.isSuccess && <p role="status" className="text-xs text-platforma-subtle">{t("agentChat.memoryCleared")}</p>}
  </div>;
}

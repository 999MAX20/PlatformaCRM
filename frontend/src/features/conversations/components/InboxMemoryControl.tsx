import { useMutation, useQueryClient } from "@tanstack/react-query";
import { inboxApi, type InboxConversation } from "../../../api/inbox";
import { Button } from "../../../components/ui/Button";
import { ErrorState } from "../../../components/ui/StateViews";
import { useActionConfirm } from "../../../components/actions/ActionConfirmProvider";
import { useI18n } from "../../../lib/i18n";
import { hasPermission } from "../../../lib/permissions";
import { useAuth } from "../../auth/AuthProvider";

export function InboxMemoryControl({ conversation }: { conversation: InboxConversation }) {
  const { t } = useI18n();
  const { user } = useAuth();
  const confirm = useActionConfirm();
  const client = useQueryClient();
  const reset = useMutation({ mutationFn: () => inboxApi.resetAIMemory(conversation.id), onSuccess: async () => {
    await client.invalidateQueries({ queryKey: ["inbox-conversations"] });
  } });
  if (!hasPermission(user, conversation.business, "conversations", "update") || !hasPermission(user, conversation.business, "ai_assistant", "suggest")) return null;
  return <div>
    <Button size="sm" variant="ghost" isLoading={reset.isPending} onClick={async () => {
      const result = await confirm({ title: t("agentChat.reset"), description: t("agentChat.resetText"), confirmLabel: t("agentChat.reset"), tone: "neutral" });
      if (result.confirmed) reset.mutate();
    }}>{t("agentChat.reset")}</Button>
    {reset.error && <ErrorState error={reset.error} />}
    {reset.isSuccess && <p role="status" className="text-xs text-platforma-subtle">{t("agentChat.memoryCleared")}</p>}
  </div>;
}

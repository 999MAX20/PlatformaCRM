import { useMutation } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { botsApi } from "../../../api/bots";
import { getApiErrorMessage } from "../../../api/client";
import { useActionConfirm } from "../../../components/actions/ActionConfirmProvider";
import { Button } from "../../../components/ui/Button";
import { ErrorState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import type { Bot } from "../../../types";

export function AgentDeleteControl({ bot, disabled, onDeleted, onPendingChange }: {
  bot: Bot; disabled: boolean; onDeleted: () => void; onPendingChange: (pending: boolean) => void;
}) {
  const { t } = useI18n();
  const confirm = useActionConfirm();
  const deletion = useMutation({ mutationFn: () => botsApi.remove(bot.id), onSuccess: onDeleted,
    onMutate: () => onPendingChange(true), onSettled: () => onPendingChange(false) });
  const remove = async () => {
    const result = await confirm({ title: t("aiAgents.deleteTitle", { name: bot.name }),
      description: t("aiAgents.deleteDescription"), confirmLabel: t("aiAgents.delete"), tone: "danger" });
    if (result.confirmed) deletion.mutate();
  };
  return <div className="mt-6 space-y-3 border-t border-platforma-border pt-5">
    {deletion.error && <ErrorState error={deletion.error} message={getApiErrorMessage(deletion.error)} />}
    <Button type="button" variant="danger" disabled={disabled || deletion.isPending} isLoading={deletion.isPending}
      onClick={() => void remove()}><Trash2 size={16} aria-hidden="true" />{t("aiAgents.delete")}</Button>
  </div>;
}

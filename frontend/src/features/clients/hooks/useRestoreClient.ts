import { useMutation, useQueryClient } from "@tanstack/react-query";
import { clientsApi } from "../../../api/clients";
import { useActionConfirm } from "../../../components/actions/ActionConfirmProvider";
import { useActionFeedback } from "../../../components/actions/useActionFeedback";
import { useI18n } from "../../../lib/i18n";
import type { Client } from "../../../types";

export function useRestoreClient() {
  const { t } = useI18n();
  const confirm = useActionConfirm();
  const queryClient = useQueryClient();
  const { notifyError, notifySuccess } = useActionFeedback();
  const mutation = useMutation({
    mutationFn: (client: Client) => clientsApi.restore(client.id),
    onSuccess: async (_, client) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["clients"] }),
        queryClient.invalidateQueries({ queryKey: ["crm-card", "client", client.id] }),
      ]);
      notifySuccess(t("clients.noticeRestored"));
    },
    onError: (error) => notifyError(error),
  });
  async function restore(client: Client) {
    if (mutation.isPending) return;
    const result = await confirm({
      title: t("clients.restoreAction"),
      description: t("clients.restoreConfirmText", { name: client.full_name }),
      confirmLabel: t("clients.restoreAction"),
    });
    if (result.confirmed) mutation.mutate(client);
  }
  return { restore, isPending: mutation.isPending };
}

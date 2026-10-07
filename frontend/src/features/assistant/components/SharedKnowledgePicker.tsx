import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { businessKnowledgeApi, setAgentKnowledgeConnection } from "../../../api/ai";
import { Button } from "../../../components/ui/Button";
import { Modal } from "../../../components/ui/Modal";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import type { Id } from "../../../types";

export function SharedKnowledgePicker({ open, onClose, businessId, agentId, connectedIds, customerAgent = false }: {
  open: boolean; onClose: () => void; businessId: Id; agentId: Id; connectedIds: Id[]; customerAgent?: boolean;
}) {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [approved, setApproved] = useState<Record<string, boolean>>({});
  const shared = useQuery({ queryKey: ["ai-shared-knowledge", businessId],
    queryFn: () => businessKnowledgeApi.listAll({ business: businessId }), enabled: open });
  const connect = useMutation({ mutationFn: (id: Id) => setAgentKnowledgeConnection(id, agentId, true, Boolean(approved[id])),
    onSuccess: async () => { await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["ai-knowledge-items", businessId, agentId] }),
      queryClient.invalidateQueries({ queryKey: ["bots"] }),
    ]); } });
  const items = (shared.data || []).filter(item => item.business === businessId && item.bot === null && !connectedIds.includes(item.id));
  return <Modal title={t("aiAgents.knowledge.connectShared")} open={open} onClose={() => { if (!connect.isPending) onClose(); }}>
    <div className="space-y-3">
      {shared.isLoading ? <LoadingState /> : shared.error ? <ErrorState error={shared.error}
        action={<Button variant="secondary" onClick={() => void shared.refetch()}>{t("common.retry")}</Button>} /> :
        items.length ? items.map(item => <article key={item.id} className="flex flex-wrap items-start justify-between gap-3 border-b border-platforma-border py-3">
          <div className="min-w-0 flex-1 basis-48"><h4 className="break-words font-semibold">{item.title}</h4>
            <p className="mt-1 line-clamp-3 whitespace-pre-wrap break-words text-sm text-platforma-subtle">{item.content}</p>
            {!item.is_active && <p className="text-sm text-platforma-subtle">{t("aiAgents.knowledge.off")}</p>}
            {customerAgent && !item.customer_visible && <label className="mt-2 flex items-start gap-2 text-sm">
              <input type="checkbox" className="mt-1" checked={Boolean(approved[item.id])} disabled={connect.isPending}
                onChange={event => setApproved(current => ({ ...current, [item.id]: event.target.checked }))} />
              {t("customerSafety.publishMaterial")}
            </label>}
          </div>
          <Button type="button" variant="secondary" disabled={connect.isPending || (customerAgent && !item.customer_visible && !approved[item.id])} isLoading={connect.isPending && connect.variables === item.id}
            onClick={() => connect.mutate(item.id)}>{t("aiAgents.knowledge.connect")}</Button>
        </article>) : <p role="status" className="text-sm text-platforma-subtle">{t("aiAgents.knowledge.noShared")}</p>}
      {connect.error && <ErrorState error={connect.error} />}
    </div>
  </Modal>;
}

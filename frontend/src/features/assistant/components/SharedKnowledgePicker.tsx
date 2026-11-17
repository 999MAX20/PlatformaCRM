import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useId, useState } from "react";
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
  const [reading, setReading] = useState<Id | null>(null);
  const id = useId();
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
      <p className="text-sm leading-6 text-platforma-subtle">{t("aiAgents.knowledge.sharedExplanation")}</p>
      <p className="text-sm leading-6 text-platforma-subtle">{t("aiAgents.knowledge.textOnly")}</p>
      {shared.isLoading ? <LoadingState /> : shared.error ? <ErrorState error={shared.error}
        action={<Button variant="secondary" onClick={() => void shared.refetch()}>{t("common.retry")}</Button>} /> :
        items.length ? items.map(item => <article key={item.id} className="flex flex-wrap items-start justify-between gap-3 border-b border-platforma-border py-3">
          <div className="min-w-0 flex-1 basis-48"><h4 className="break-words font-semibold">{item.title}</h4>
            <p id={`${id}-content-${item.id}`} className={`mt-1 whitespace-pre-wrap break-words text-sm leading-6 text-platforma-subtle ${reading === item.id ? "" : "line-clamp-3"}`}>{item.content}</p>
            <Button type="button" variant="ghost" className="mt-1" aria-expanded={reading === item.id} aria-controls={`${id}-content-${item.id}`}
              onClick={() => setReading(current => current === item.id ? null : item.id)}>{t(reading === item.id ? "aiAgents.knowledge.collapseText" : "aiAgents.knowledge.readFull")}</Button>
            {!item.is_active && <p className="text-sm text-platforma-subtle">{t("aiAgents.knowledge.off")}</p>}
            {customerAgent && !item.customer_visible && <div className="mt-3 space-y-2">
              <p id={`${id}-permission-${item.id}`} className="text-sm leading-6 text-platforma-subtle">{t("aiAgents.knowledge.sharedPermission")}</p>
              <label className="flex min-h-11 items-start gap-3 text-sm">
              <input type="checkbox" className="mt-1" checked={Boolean(approved[item.id])} disabled={connect.isPending}
                aria-describedby={`${id}-permission-${item.id}`}
                onChange={event => setApproved(current => ({ ...current, [item.id]: event.target.checked }))} />
              {t("customerSafety.publishMaterial")}
            </label></div>}
          </div>
          <Button type="button" variant="secondary" disabled={connect.isPending || (customerAgent && !item.customer_visible && !approved[item.id])} isLoading={connect.isPending && connect.variables === item.id}
            onClick={() => connect.mutate(item.id)}>{t("aiAgents.knowledge.connect")}</Button>
        </article>) : <p role="status" className="text-sm text-platforma-subtle">{t("aiAgents.knowledge.noShared")}</p>}
      {connect.error && <ErrorState error={connect.error} />}
    </div>
  </Modal>;
}

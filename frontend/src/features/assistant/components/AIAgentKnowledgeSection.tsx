import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { setAgentKnowledgeConnection } from "../../../api/ai";
import { Button } from "../../../components/ui/Button";
import { Modal } from "../../../components/ui/Modal";
import { ErrorState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import type { BusinessKnowledgeItem, Id } from "../../../types";
import { SharedKnowledgePicker } from "./SharedKnowledgePicker";
import { KnowledgeEditor, type KnowledgeDraftGuard, type KnowledgeTemplate } from "./KnowledgeEditor";
import { KnowledgeMaterialDetails, KnowledgeStatus } from "./KnowledgeMaterialDetails";

export function KnowledgeSection({ agentId, businessId, items, canManage, customerAgent = false, sourceEnabled = true, ...guard }: KnowledgeDraftGuard & {
  agentId: Id; businessId: Id; items: BusinessKnowledgeItem[]; canManage: boolean; customerAgent?: boolean; sourceEnabled?: boolean;
}) {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [editor, setEditor] = useState<{ item: BusinessKnowledgeItem | null; template?: KnowledgeTemplate } | null>(null);
  const [sharedOpen, setSharedOpen] = useState(false);
  const [viewing, setViewing] = useState<BusinessKnowledgeItem | null>(null);
  const categories = ["business", "sales", "policy", "faq"];
  const templates = [
    { key: "prices", category: "sales" }, { key: "schedule", category: "business" },
    { key: "booking", category: "policy" }, { key: "faq", category: "faq" },
  ].map(({ key, category }) => ({ title: t(`aiAgents.knowledge.template.${key}`), category, hint: t(`aiAgents.knowledge.template.${key}Content`) }));
  const disconnect = useMutation({ mutationFn: (id: Id) => setAgentKnowledgeConnection(id, agentId, false),
    onSuccess: async () => { await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["ai-knowledge-items", businessId, agentId] }),
      queryClient.invalidateQueries({ queryKey: ["bots"] }),
    ]); } });

  return <>
    <section className="space-y-5">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1 basis-64">
          <h3 className="text-base font-semibold text-platforma-ink">{t("aiAgents.knowledge.agentTitle")}</h3>
          <p className="mt-2 max-w-2xl text-sm leading-5 text-platforma-subtle">{t("aiAgents.knowledge.agentScope")}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="secondary" disabled={!canManage} onClick={() => setSharedOpen(true)}>{t("aiAgents.knowledge.connectShared")}</Button>
          <Button type="button" disabled={!canManage} onClick={() => setEditor({ item: null })}><Plus size={16} aria-hidden="true" />{t("aiAgents.knowledge.add")}</Button>
        </div>
      </header>
      <div>
        <h4 className="text-sm font-semibold text-platforma-ink">{t("aiAgents.knowledge.addByTopic")}</h4>
        <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
          {templates.map(template => <button key={template.category} type="button" disabled={!canManage}
            className="platforma-focus-ring group min-h-11 rounded-control border border-platforma-border p-3 text-left transition hover:border-brand-200 hover:bg-brand-50 disabled:cursor-not-allowed disabled:border-disabled-border disabled:bg-disabled-surface"
            onClick={() => setEditor({ item: null, template })}>
            <span className="text-sm font-semibold text-platforma-ink group-disabled:text-disabled-content">{template.title}</span>
            <span className="mt-1 block text-xs text-platforma-subtle group-disabled:text-disabled-content">{t(`aiAgents.knowledge.category.${template.category}`)}</span>
          </button>)}
        </div>
      </div>
      {disconnect.error && <ErrorState error={disconnect.error} />}
      <div className="divide-y divide-platforma-border border-t border-platforma-border">
        {items.length ? items.map(item => <article key={item.id} className="flex flex-wrap items-start justify-between gap-3 py-4">
          <div className="min-w-0 flex-1 basis-48">
            <h4 className="min-w-0 break-words text-sm font-semibold text-platforma-ink">
              <button type="button" className="platforma-focus-ring min-h-11 rounded-control text-left underline decoration-platforma-border underline-offset-4 hover:decoration-current"
                onClick={() => setViewing(item)}>{item.title}</button>
            </h4>
            <div className="flex flex-wrap items-center gap-2 text-xs text-platforma-subtle">
              <span>{t(item.bot === null ? "aiAgents.knowledge.sharedMaterial" : "aiAgents.knowledge.ownMaterial")}</span>
              <span>{categories.includes(item.category || "business") ? t(`aiAgents.knowledge.category.${item.category || "business"}`) : item.category}</span>
              <KnowledgeStatus item={item} customerAgent={customerAgent} sourceEnabled={sourceEnabled} />
            </div>
            <p className="mt-2 line-clamp-2 whitespace-pre-wrap break-words text-sm leading-5 text-platforma-subtle">{item.content}</p>
          </div>
          {item.bot === null ? <Button type="button" variant="secondary" disabled={!canManage || disconnect.isPending}
            isLoading={disconnect.isPending && disconnect.variables === item.id} onClick={() => disconnect.mutate(item.id)}>{t("aiAgents.knowledge.disconnect")}</Button>
            : <Button type="button" variant="secondary" disabled={!canManage} onClick={() => setEditor({ item })}>{t("aiAgents.knowledge.edit")}</Button>}
        </article>) : <div className="py-4" role="status">
          <h4 className="text-sm font-semibold text-platforma-ink">{t("aiAgents.knowledge.emptyTitle")}</h4>
          <p className="mt-2 text-sm leading-5 text-platforma-subtle">{t("aiAgents.knowledge.emptyText")}</p>
        </div>}
      </div>
    </section>
    {sharedOpen && <SharedKnowledgePicker open onClose={() => setSharedOpen(false)} businessId={businessId} agentId={agentId}
      customerAgent={customerAgent} connectedIds={items.filter(item => item.bot === null).map(item => item.id)} />}
    <Modal title={viewing?.title || t("aiAgents.knowledge.content")} open={Boolean(viewing)} onClose={() => setViewing(null)}>
      {viewing && <KnowledgeMaterialDetails item={viewing} customerAgent={customerAgent} sourceEnabled={sourceEnabled} />}
    </Modal>
    {editor && <KnowledgeEditor {...editor} {...guard} agentId={agentId} businessId={businessId} canManage={canManage} customerAgent={customerAgent} onClose={() => setEditor(null)} />}
  </>;
}

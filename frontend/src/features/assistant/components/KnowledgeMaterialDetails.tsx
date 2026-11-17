import { cn } from "../../../lib/cn";
import { useI18n } from "../../../lib/i18n";
import type { BusinessKnowledgeItem } from "../../../types";

export function KnowledgeStatus({ item, customerAgent, sourceEnabled = true }: {
  item: BusinessKnowledgeItem; customerAgent: boolean; sourceEnabled?: boolean;
}) {
  const { t } = useI18n();
  const available = item.is_active && sourceEnabled && (!customerAgent || item.customer_visible);
  const label = !item.is_active ? "aiAgents.knowledge.off" : !sourceEnabled ? "aiAgents.knowledge.sourceOff"
    : customerAgent && !item.customer_visible ? "aiAgents.knowledge.notApproved" : "aiAgents.knowledge.available";
  return <span className={cn("rounded-full px-2 py-1 text-xs font-semibold", available
    ? "bg-[var(--platforma-success-soft)] text-platforma-success" : "bg-surface-muted text-platforma-subtle")}>{t(label)}</span>;
}

export function KnowledgeMaterialDetails({ item, customerAgent, sourceEnabled = true }: {
  item: BusinessKnowledgeItem; customerAgent: boolean; sourceEnabled?: boolean;
}) {
  const { t } = useI18n();
  const category = ["business", "sales", "policy", "faq"].includes(item.category || "business")
    ? t(`aiAgents.knowledge.category.${item.category || "business"}`) : item.category;
  return <div className="space-y-4">
    <div className="flex flex-wrap items-center gap-3 text-sm text-platforma-subtle">
      <span>{category}</span>
      <span>{t(item.bot === null ? "aiAgents.knowledge.sharedMaterial" : "aiAgents.knowledge.ownMaterial")}</span>
      <KnowledgeStatus item={item} customerAgent={customerAgent} sourceEnabled={sourceEnabled} />
    </div>
    <p className="whitespace-pre-wrap break-words text-sm leading-6 text-platforma-ink">{item.content}</p>
  </div>;
}

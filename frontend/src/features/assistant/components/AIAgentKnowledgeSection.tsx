import { useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { BookOpen, Plus, Save, Settings } from "lucide-react";

import { businessKnowledgeApi, setAgentKnowledgeConnection } from "../../../api/ai";
import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import { Modal } from "../../../components/ui/Modal";
import { Textarea } from "../../../components/ui/Textarea";
import { ErrorState } from "../../../components/ui/StateViews";
import { cn } from "../../../lib/cn";
import { useI18n } from "../../../lib/i18n";
import type { BusinessKnowledgeItem, Id } from "../../../types";
import { FieldHint } from "./AIAgentsShared";
import { SharedKnowledgePicker } from "./SharedKnowledgePicker";
export function KnowledgeSection({ agentId, businessId, items, canManage }: { agentId: Id; businessId: Id; items: BusinessKnowledgeItem[]; canManage: boolean }) {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [sharedOpen, setSharedOpen] = useState(false);
  const [editing, setEditing] = useState<BusinessKnowledgeItem | null>(null);
  const [draft, setDraft] = useState({ title: "", category: "business", content: "", is_active: true });
  const [submitted, setSubmitted] = useState(false);
  const titleRef = useRef<HTMLInputElement>(null);
  const contentRef = useRef<HTMLTextAreaElement>(null);
  const titleMissing = !draft.title.trim();
  const contentMissing = !draft.content.trim();
  const categories = ["business", "sales", "policy", "faq"];
  const categoryLabel = (value: string) => categories.includes(value) ? t(`aiAgents.knowledge.category.${value}`) : value;
  const saveKnowledge = useMutation({
    mutationFn: () => {
      const payload = { ...draft, title: draft.title.trim(), content: draft.content.trim(), category: draft.category.trim(), business: businessId, bot: agentId };
      return editing ? businessKnowledgeApi.update({ id: editing.id, payload }) : businessKnowledgeApi.create(payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-knowledge-items"] });
      queryClient.invalidateQueries({ queryKey: ["bots"] });
      setOpen(false);
      setEditing(null);
      setDraft({ title: "", category: "business", content: "", is_active: true });
    },
  });
  const disconnect = useMutation({ mutationFn: (id: Id) => setAgentKnowledgeConnection(id, agentId, false),
    onSuccess: async () => { await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["ai-knowledge-items", businessId, agentId] }),
      queryClient.invalidateQueries({ queryKey: ["bots"] }),
    ]); } });

  const openEditor = (item?: BusinessKnowledgeItem) => {
    saveKnowledge.reset();
    setSubmitted(false);
    if (item) {
      setEditing(item);
      setDraft({ title: item.title, category: item.category || "business", content: item.content, is_active: item.is_active });
    } else {
      setEditing(null);
      setDraft({ title: "", category: "business", content: "", is_active: true });
    }
    setOpen(true);
  };

  const knowledgeTemplates = [
    { title: t("aiAgents.knowledge.template.prices"), category: "sales", content: t("aiAgents.knowledge.template.pricesContent") },
    { title: t("aiAgents.knowledge.template.schedule"), category: "business", content: t("aiAgents.knowledge.template.scheduleContent") },
    { title: t("aiAgents.knowledge.template.booking"), category: "policy", content: t("aiAgents.knowledge.template.bookingContent") },
    { title: t("aiAgents.knowledge.template.faq"), category: "faq", content: t("aiAgents.knowledge.template.faqContent") },
  ];

  const openTemplate = (template: { title: string; category: string; content: string }) => {
    saveKnowledge.reset();
    setSubmitted(false);
    setEditing(null);
    setDraft({ ...template, is_active: true });
    setOpen(true);
  };

  return (
    <>
      <section className="space-y-3">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="text-base font-semibold text-platforma-ink">{t("aiAgents.knowledge.agentTitle")}</h3>
          <div className="flex flex-wrap gap-2">
          <Button type="button" variant="secondary" disabled={!canManage} onClick={() => setSharedOpen(true)}>{t("aiAgents.knowledge.connectShared")}</Button>
          <Button type="button" className="min-h-11 sm:min-h-10" disabled={!canManage} onClick={() => openEditor()}>
            <Plus size={16} /> {t("aiAgents.knowledge.add")}
          </Button>
          </div>
        </header>
        <div className="border-b border-platforma-border pb-3 text-sm leading-5 text-platforma-subtle">
          <p>{t("aiAgents.knowledge.agentScope")}</p>
        </div>
        {disconnect.error && <ErrorState error={disconnect.error} />}
        <div className="divide-y divide-platforma-border">
          {items.length ? items.map(item => (
            <article key={item.id} className="flex flex-wrap items-start justify-between gap-3 py-3 first:pt-0">
              <div className="min-w-0 flex-1 basis-48">
                <div className="flex flex-wrap items-center gap-2">
                  <h4 className="break-words text-sm font-semibold text-platforma-ink">{item.title}</h4>
                  {item.bot === null && <span className="text-xs text-platforma-subtle">{t("aiAgents.knowledge.sharedMaterial")}</span>}
                  <span className={cn("rounded-full px-2 py-0.5 text-xs font-semibold", item.is_active ? "bg-[var(--platforma-success-soft)] text-platforma-success" : "bg-surface-muted text-platforma-subtle")}>
                    {item.is_active ? t("aiAgents.knowledge.active") : t("aiAgents.knowledge.off")}
                  </span>
                </div>
                <p className="mt-1 text-xs text-platforma-subtle">{categoryLabel(item.category || "business")}</p>
                <p className="mt-1 line-clamp-2 whitespace-pre-wrap break-words text-sm leading-5 text-platforma-subtle">{item.content}</p>
              </div>
              {item.bot === null ? <Button type="button" variant="secondary" disabled={!canManage || disconnect.isPending}
                isLoading={disconnect.isPending && disconnect.variables === item.id} onClick={() => disconnect.mutate(item.id)}>{t("aiAgents.knowledge.disconnect")}</Button> :
              <Button type="button" className="min-h-11 sm:min-h-10" variant="secondary" disabled={!canManage} onClick={() => openEditor(item)}>
                <Settings size={16} /> {t("aiAgents.configure")}
              </Button>}
            </article>
          )) : (
            <div className="py-3">
              <div className="flex items-center gap-2">
                <BookOpen className="text-brand-600" size={20} />
                <h4 className="text-sm font-semibold text-platforma-ink">{t("aiAgents.knowledge.emptyTitle")}</h4>
              </div>
              <p className="mt-2 text-sm leading-5 text-platforma-subtle">{t("aiAgents.knowledge.emptyText")}</p>
              <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
                {knowledgeTemplates.map(template => (
                  <button key={template.title} type="button" disabled={!canManage}
                    className="platforma-focus-ring group min-h-11 rounded-control border border-platforma-border p-3 text-left transition hover:border-brand-200 hover:bg-brand-50 disabled:cursor-not-allowed disabled:border-disabled-border disabled:bg-disabled-surface"
                    onClick={() => openTemplate(template)}>
                    <span className="text-sm font-semibold text-platforma-ink group-disabled:text-disabled-content">{template.title}</span>
                    <span className="mt-1 block text-xs text-platforma-subtle group-disabled:text-disabled-content">{t(`aiAgents.knowledge.category.${template.category}`)}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>
      {sharedOpen && <SharedKnowledgePicker open onClose={() => setSharedOpen(false)} businessId={businessId} agentId={agentId}
        connectedIds={items.filter(item => item.bot === null).map(item => item.id)} />}

      <Modal title={editing ? t("aiAgents.knowledge.editTitle") : t("aiAgents.knowledge.newTitle")} open={open} onClose={() => { if (!saveKnowledge.isPending) setOpen(false); }}>
        <form
          noValidate
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            if (!canManage || saveKnowledge.isPending) return;
            setSubmitted(true);
            if (titleMissing || contentMissing) {
              (titleMissing ? titleRef.current : contentRef.current)?.focus();
              return;
            }
            saveKnowledge.mutate();
          }}
        >
          {saveKnowledge.error ? <ErrorState error={saveKnowledge.error} message={getApiErrorMessage(saveKnowledge.error)} /> : null}
          <Input ref={titleRef} required maxLength={255} disabled={!canManage || saveKnowledge.isPending} error={submitted && titleMissing ? t("aiWorkspace.titleRequired") : undefined} label={t("aiAgents.knowledge.title")} value={draft.title} onChange={(event) => setDraft((current) => ({ ...current, title: event.target.value }))} />
          <FieldHint>{t("aiAgents.hint.knowledgeTitle")}</FieldHint>
          <Select disabled={!canManage || saveKnowledge.isPending} label={t("aiAgents.knowledge.category")} value={draft.category}
            options={[...categories, ...(categories.includes(draft.category) ? [] : [draft.category])].map(value => ({ value, label: categoryLabel(value) }))}
            onChange={(event) => setDraft((current) => ({ ...current, category: event.target.value }))} />
          <FieldHint>{t("aiAgents.hint.knowledgeCategory")}</FieldHint>
          <Textarea ref={contentRef} required disabled={!canManage || saveKnowledge.isPending} error={submitted && contentMissing ? t("aiWorkspace.contentRequired") : undefined} label={t("aiAgents.knowledge.content")} value={draft.content} onChange={(event) => setDraft((current) => ({ ...current, content: event.target.value }))} />
          <FieldHint>{t("aiAgents.hint.knowledgeContent")}</FieldHint>
          <label className="inline-flex items-center gap-2 text-sm font-bold text-platforma-subtle">
            <input type="checkbox" disabled={!canManage || saveKnowledge.isPending} checked={draft.is_active} onChange={(event) => setDraft((current) => ({ ...current, is_active: event.target.checked }))} />
            {t("aiAgents.knowledge.useInContext")}
          </label>
          <FieldHint>{t("aiAgents.hint.knowledgeActive")}</FieldHint>
          <p className="text-sm text-platforma-subtle">{t("aiWorkspace.requiredKnowledge")}</p>
          <Button type="submit" disabled={!canManage} isLoading={saveKnowledge.isPending}>
            <Save size={16} /> {t("common.save")}
          </Button>
        </form>
      </Modal>
    </>
  );
}

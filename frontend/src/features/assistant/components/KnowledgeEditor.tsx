import { useEffect, useId, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { businessKnowledgeApi } from "../../../api/ai";
import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import { Modal } from "../../../components/ui/Modal";
import { Textarea } from "../../../components/ui/Textarea";
import { ErrorState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import type { BusinessKnowledgeItem, Id } from "../../../types";

export type KnowledgeTemplate = { title: string; category: string; hint: string };
export type KnowledgeDraftGuard = {
  onDirtyChange: (dirty: boolean) => void;
  navigationBlocked: boolean;
  onCancelNavigation: () => void;
  onDiscardNavigation: () => void;
};

export function KnowledgeEditor({ item, template, agentId, businessId, canManage, customerAgent, onClose,
  onDirtyChange, navigationBlocked, onCancelNavigation, onDiscardNavigation,
}: KnowledgeDraftGuard & {
  item: BusinessKnowledgeItem | null; template?: KnowledgeTemplate;
  agentId: Id; businessId: Id; canManage: boolean; customerAgent: boolean; onClose: () => void;
}) {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const id = useId();
  const [initial] = useState(() => ({ title: item?.title || template?.title || "", category: item?.category || template?.category || "business",
    content: item?.content || "", is_active: item?.is_active ?? true, customer_visible: item?.customer_visible ?? false }));
  const [draft, setDraft] = useState(initial);
  const [submitted, setSubmitted] = useState(false);
  const [confirmClose, setConfirmClose] = useState(false);
  const titleRef = useRef<HTMLInputElement>(null);
  const contentRef = useRef<HTMLTextAreaElement>(null);
  const dirty = JSON.stringify(draft) !== JSON.stringify(initial);
  const titleMissing = !draft.title.trim();
  const contentMissing = !draft.content.trim();
  const categories = ["business", "sales", "policy", "faq"];
  const save = useMutation({
    mutationFn: () => {
      const payload = { ...draft, title: draft.title.trim(), content: draft.content.trim(), business: businessId, bot: agentId };
      return item ? businessKnowledgeApi.update({ id: item.id, payload }) : businessKnowledgeApi.create(payload);
    },
    onSuccess: async () => {
      if (navigationBlocked) onCancelNavigation();
      await Promise.all([queryClient.invalidateQueries({ queryKey: ["ai-knowledge-items"] }), queryClient.invalidateQueries({ queryKey: ["bots"] })]);
      onClose();
    },
  });
  useEffect(() => { onDirtyChange(dirty || save.isPending); }, [dirty, save.isPending, onDirtyChange]);
  useEffect(() => () => onDirtyChange(false), [onDirtyChange]);
  const requestClose = () => { if (!save.isPending) { if (dirty) setConfirmClose(true); else onClose(); } };
  const cancelClose = () => { setConfirmClose(false); if (navigationBlocked) onCancelNavigation(); };
  const disabled = !canManage || save.isPending;
  const hintClass = "mt-2 text-xs leading-5 text-platforma-subtle";
  return <>
    <Modal title={t(item ? "aiAgents.knowledge.editTitle" : "aiAgents.knowledge.newTitle")} open onClose={requestClose}
      footer={<div className="flex flex-wrap justify-end gap-2">
        <Button type="button" variant="secondary" disabled={save.isPending} onClick={requestClose}>{t("common.cancel")}</Button>
        <Button type="submit" form={id} disabled={!canManage} isLoading={save.isPending}>{t("common.save")}</Button>
      </div>}>
      <form id={id} noValidate className="space-y-4" onSubmit={event => {
        event.preventDefault();
        if (disabled) return;
        setSubmitted(true);
        if (titleMissing || contentMissing) { (titleMissing ? titleRef.current : contentRef.current)?.focus(); return; }
        save.mutate();
      }}>
        {save.error && <ErrorState error={save.error} message={getApiErrorMessage(save.error)} />}
        <Input ref={titleRef} required maxLength={255} disabled={disabled} label={t("aiAgents.knowledge.title")}
          error={submitted && titleMissing ? t("aiWorkspace.titleRequired") : undefined}
          value={draft.title} onChange={event => setDraft(current => ({ ...current, title: event.target.value }))} />
        <Select disabled={disabled} label={t("aiAgents.knowledge.category")} value={draft.category}
          options={[...categories, ...(categories.includes(draft.category) ? [] : [draft.category])].map(value => ({ value, label: categories.includes(value) ? t(`aiAgents.knowledge.category.${value}`) : value }))}
          onChange={event => setDraft(current => ({ ...current, category: event.target.value }))} />
        <div>
          <Textarea ref={contentRef} required rows={8} className="min-h-48" disabled={disabled} label={t("aiAgents.knowledge.content")}
            aria-describedby={`${id}-content-hint`} error={submitted && contentMissing ? t("aiWorkspace.contentRequired") : undefined}
            value={draft.content} onChange={event => setDraft(current => ({ ...current, content: event.target.value }))} />
          <p id={`${id}-content-hint`} className={hintClass}>{template?.hint || t("aiAgents.hint.knowledgeContent")} {t("aiAgents.knowledge.textOnly")}</p>
        </div>
        <label className="flex min-h-11 items-center gap-3 text-sm font-semibold text-platforma-subtle">
          <input type="checkbox" disabled={disabled} checked={draft.is_active} onChange={event => setDraft(current => ({ ...current, is_active: event.target.checked }))} />
          {t("aiAgents.knowledge.enableMaterial")}
        </label>
        {customerAgent && <div>
          <label className="flex min-h-11 items-start gap-3 text-sm text-platforma-subtle">
            <input type="checkbox" className="mt-1" disabled={disabled} checked={draft.customer_visible}
              aria-describedby={`${id}-audience-hint`} onChange={event => setDraft(current => ({ ...current, customer_visible: event.target.checked }))} />
            {t("customerSafety.publishMaterial")}
          </label>
          <p id={`${id}-audience-hint`} className={hintClass}>{t("aiAgents.knowledge.customerUseHint")}</p>
        </div>}
        <p className="text-xs leading-5 text-platforma-subtle">{t("aiWorkspace.requiredKnowledge")}</p>
      </form>
    </Modal>
    <Modal title={t("aiAgents.knowledge.unsavedTitle")} open={confirmClose || navigationBlocked} onClose={cancelClose} size="sm">
      <p className="text-sm leading-6 text-platforma-subtle">{t("aiAgents.knowledge.unsavedText")}</p>
      <div className="mt-5 flex flex-wrap justify-end gap-2">
        <Button type="button" variant="secondary" onClick={cancelClose}>{t("aiAgents.knowledge.keepEditing")}</Button>
        <Button type="button" variant="warning" disabled={save.isPending} onClick={() => {
          if (navigationBlocked) onDiscardNavigation();
          onClose();
        }}>{t("actions.discardChanges")}</Button>
      </div>
    </Modal>
  </>;
}

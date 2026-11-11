import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { useActionConfirm } from "../../components/actions/ActionConfirmProvider";
import { DraftGuard } from "../../components/actions/DraftGuard";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { ErrorState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import type { Id } from "../../types";

export const managementQueryKeys = ["management", "branches", "services", "resources", "branch-configuration", "branch-catalog", "working-hours", "available-slots"];

export function FormShell({ title, onClose, save, children }: { title: string; onClose: () => void; save: () => Promise<unknown>; children: ReactNode }) {
  const { t } = useI18n();
  const [dirty, setDirty] = useState(false);
  const confirm = useActionConfirm();
  const cache = useQueryClient();
  const mutation = useMutation({ mutationFn: save, onSuccess: async () => {
    setDirty(false);
    await Promise.all(managementQueryKeys.map(key => cache.invalidateQueries({ queryKey: [key] })));
    onClose();
  } });
  const close = async () => {
    if (mutation.isPending) return;
    if (dirty && !(await confirm({ title: t("workingHours.discardChanges"), confirmLabel: t("actions.discardChanges"), tone: "warning" })).confirmed) return;
    onClose();
  };
  return <Modal open title={title} onClose={() => void close()} size="lg" closeOnBackdrop={!mutation.isPending}>
    <DraftGuard dirty={dirty} pending={mutation.isPending} />
    <form className="space-y-5" onChange={() => setDirty(true)} onSubmit={event => { event.preventDefault(); mutation.mutate(); }}>
      {mutation.error && <ErrorState error={mutation.error} />}
      <fieldset disabled={mutation.isPending} className="min-w-0 space-y-5">{children}</fieldset>
      <div className="sticky bottom-0 flex flex-wrap gap-2 border-t border-platforma-border bg-white py-3">
        <Button type="submit" isLoading={mutation.isPending}>{t("common.save")}</Button>
        <Button type="button" variant="secondary" disabled={mutation.isPending} onClick={() => void close()}>{t("common.cancel")}</Button>
      </div>
    </form>
  </Modal>;
}

export function EntityChoices({ label, options, selected, onChange, empty }: { label: string; options: { id: Id; name: string }[]; selected: Id[]; onChange: (ids: Id[]) => void; empty: string }) {
  return <fieldset className="min-w-0"><legend className="mb-2 text-sm font-medium">{label}</legend>
    {options.length ? <div className="grid min-w-0 gap-1 sm:grid-cols-2">{options.map(option => <label key={option.id} className="flex min-h-11 cursor-pointer items-center gap-2 rounded-control px-2 text-sm hover:bg-surface-hover">
      <input type="checkbox" className="size-4 shrink-0 accent-brand-600" checked={selected.includes(option.id)} onChange={event => onChange(event.target.checked ? [...selected, option.id] : selected.filter(id => id !== option.id))} />
      <span className="min-w-0 break-words">{option.name}</span>
    </label>)}</div> : <p className="text-sm text-platforma-subtle">{empty}</p>}
  </fieldset>;
}

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { leadFormFieldsApi, leadFormsApi } from "../../../api/leadForms";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Modal } from "../../../components/ui/Modal";
import { EmptyState, ErrorState, ForbiddenState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import { hasPermission } from "../../../lib/permissions";
import type { Id, LeadFormField } from "../../../types";
import { useAuth } from "../../auth/AuthProvider";
import { LeadCaptureFieldsEditor } from "./LeadCaptureFieldsEditor";

export function LeadCaptureFormsModal({ business, onClose }: { business: Id; onClose: () => void }) {
  const { t } = useI18n();
  const { user } = useAuth();
  const cache = useQueryClient();
  const [page, setPage] = useState(1);
  const [formId, setFormId] = useState<Id | null>(null);
  const [editing, setEditing] = useState<Id | "new" | null>(null);
  const [removing, setRemoving] = useState<LeadFormField | null>(null);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [savingField, setSavingField] = useState(false);
  const key = ["lead-capture-forms", business, user?.id];
  const forms = useQuery({ queryKey: [...key, "list", page], queryFn: () => leadFormsApi.listPage(business, page), retry: false });
  const form = useQuery({ queryKey: [...key, "detail", formId], queryFn: () => leadFormsApi.get(formId!), enabled: formId !== null, retry: false });
  const field = useQuery({ queryKey: [...key, "field", editing], queryFn: () => {
    if (typeof editing !== "number") throw new Error("No field selected");
    return leadFormFieldsApi.get(editing);
  }, enabled: typeof editing === "number", retry: false });
  const canCreate = hasPermission(user, business, "leads", "create");
  const canUpdate = hasPermission(user, business, "leads", "update");
  const canDelete = hasPermission(user, business, "leads", "delete");
  const create = useMutation({ mutationFn: () => leadFormsApi.create({ business, name: name.trim(), title: name.trim() }),
    onSuccess: async row => { await cache.invalidateQueries({ queryKey: key }); setFormId(row.id); setCreating(false); setName(""); } });
  const remove = useMutation({ mutationFn: () => leadFormFieldsApi.remove(removing!.id),
    onSuccess: async () => { await cache.invalidateQueries({ queryKey: key }); setRemoving(null); } });
  const saved = async () => { await cache.invalidateQueries({ queryKey: key }); setEditing(null); };
  const back = () => { setEditing(null); setRemoving(null); setFormId(null); remove.reset(); };
  return <Modal open title={t("settings.leadFormsTitle")} onClose={() => { if (!savingField && !create.isPending && !remove.isPending) onClose(); }} size="lg" testId="lead-capture-forms">
    {formId === null ? <div className="space-y-4">
      {forms.isPending ? <LoadingState /> : forms.isError ? <ErrorState error={forms.error} action={<Button onClick={() => void forms.refetch()}>{t("common.retry")}</Button>} /> : <>
        {forms.data.results.map(row => <Button key={row.id} variant="secondary" className="w-full justify-start" onClick={() => setFormId(row.id)}>{row.name}</Button>)}
        {!forms.data.results.length && <EmptyState title={t("settings.noLeadFormsTitle")} />}
        {(forms.data.previous || forms.data.next) && <nav className="flex justify-between" aria-label={t("captureFields.pages")}>
          <Button variant="secondary" disabled={!forms.data.previous} onClick={() => setPage(value => value - 1)}>{t("captureFields.previous")}</Button>
          <Button variant="secondary" disabled={!forms.data.next} onClick={() => setPage(value => value + 1)}>{t("captureFields.next")}</Button>
        </nav>}
        {canCreate && (creating ? <form className="space-y-3" onSubmit={event => { event.preventDefault(); create.mutate(); }}>
          <Input label={t("captureFields.formName")} value={name} required maxLength={255} disabled={create.isPending} onChange={event => { setName(event.target.value); create.reset(); }} />
          {create.isError && <ErrorState error={create.error} />}
          <div className="flex gap-2"><Button type="submit" disabled={!name.trim()} isLoading={create.isPending}>{t("settings.createForm")}</Button>
            <Button type="button" variant="secondary" disabled={create.isPending} onClick={() => setCreating(false)}>{t("common.cancel")}</Button></div>
        </form> : <Button onClick={() => setCreating(true)}>{t("settings.createForm")}</Button>)}
      </>}
    </div> : <div className="space-y-4">
      <Button variant="secondary" onClick={back} disabled={remove.isPending || savingField}>{t("common.back")}</Button>
      {form.isPending ? <LoadingState /> : form.isError ? <ErrorState error={form.error} action={<Button onClick={() => void form.refetch()}>{t("common.retry")}</Button>} /> : String(form.data.business) !== String(business) ? <ForbiddenState /> : <>
        <h3 className="text-base font-semibold text-platforma-ink">{form.data.name}</h3>
        {editing !== null ? editing === "new" ? <LeadCaptureFieldsEditor key="new" form={formId} onSaved={saved} onCancel={() => setEditing(null)} onBusyChange={setSavingField} />
          : field.isPending ? <LoadingState /> : field.isError ? <ErrorState error={field.error} action={<Button onClick={() => void field.refetch()}>{t("common.retry")}</Button>} />
          : String(field.data.form) === String(formId) ? <LeadCaptureFieldsEditor key={field.data.id} form={formId} initial={field.data} onSaved={saved} onCancel={() => setEditing(null)} onBusyChange={setSavingField} /> : <ForbiddenState />
        : removing ? <div className="space-y-3">
          <p>{t("captureFields.deleteConfirm", { label: removing.label })}</p>
          {remove.isError && <ErrorState error={remove.error} />}
          <div className="flex flex-wrap gap-2"><Button variant="danger" isLoading={remove.isPending} onClick={() => remove.mutate()}>{t("settings.delete")}</Button>
            <Button variant="secondary" disabled={remove.isPending} onClick={() => { setRemoving(null); remove.reset(); }}>{t("common.cancel")}</Button></div>
        </div> : <>
          {!form.data.fields.length && <EmptyState title={t("captureFields.empty")} />}
          <ul className="divide-y divide-platforma-border">{form.data.fields.map(row => <li key={row.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
            <span className="min-w-0 break-words text-sm font-medium">{row.label}{row.is_required ? " *" : ""}</span>
            <div className="flex gap-2">{canUpdate && <Button variant="secondary" onClick={() => setEditing(row.id)} aria-label={`${t("settings.edit")}: ${row.label}`}>{t("settings.edit")}</Button>}
              {canDelete && <Button variant="secondary" onClick={() => { setRemoving(row); remove.reset(); }} aria-label={`${t("settings.delete")}: ${row.label}`}>{t("settings.delete")}</Button>}</div>
          </li>)}</ul>
          {canCreate && <Button onClick={() => setEditing("new")}>{t("settings.redesign.addField")}</Button>}
        </>}
      </>}
    </div>}
  </Modal>;
}

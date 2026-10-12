import { useMutation, useQuery } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { tasksApi, type TaskCreatePayload } from "../../../api/tasks";
import { normalizeAppError } from "../../../api/appError";
import type { TaskRelationType } from "../../../api/taskRelations";
import { useActionConfirm } from "../../../components/actions/ActionConfirmProvider";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Modal } from "../../../components/ui/Modal";
import { Select } from "../../../components/ui/Select";
import { ErrorState } from "../../../components/ui/StateViews";
import { FieldErrorSummary } from "../../../components/ui/FieldErrorSummary";
import { Textarea } from "../../../components/ui/Textarea";
import { useAuth } from "../../auth/AuthProvider";
import { hasPermission } from "../../../lib/permissions";
import { useI18n } from "../../../lib/i18n";
import type { Id, Task } from "../../../types";
import { taskDateInput, taskDateISO } from "../workspaceUtils";
import { TaskRelationPicker } from "./TaskRelationPicker";
import { TaskDraftGuard } from "./TaskDraftGuard";

const links: TaskRelationType[] = ["client", "lead", "deal", "appointment", "conversation", "parent_task", "specialist"];
const resources = { client: "clients", lead: "leads", deal: "deals", appointment: "appointments", conversation: "conversations", parent_task: "tasks", specialist: "settings" } as const;

export function TaskEditor({ task, business, zone, initialClient, parentDirty = false, onClose, onSaved }: {
  task?: Task; business: Id; zone: string; initialClient?: Id; parentDirty?: boolean; onClose: () => void; onSaved: (task: Task) => void;
}) {
  const { t } = useI18n();
  const { user } = useAuth();
  const confirm = useActionConfirm();
  const [version, setVersion] = useState(task);
  const initial = useRef<Record<string, string>>({
    title: task?.title || "", description: task?.description || "", priority: task?.priority || "normal",
    assignee: String(task ? task.assignee ?? "" : user?.id ?? ""), due_at: taskDateInput(task?.due_at, zone), reminder_at: taskDateInput(task?.reminder_at, zone),
    ...Object.fromEntries(links.map(field => [field, String(task?.[field] ?? (field === "client" ? initialClient : "") ?? "")])),
  }).current;
  const [draft, setDraft] = useState(initial);
  const [relation, setRelation] = useState<TaskRelationType>("client");
  const [more, setMore] = useState(Boolean(task?.description || task?.relations?.length || initialClient));
  const attempt = useRef({ signature: "", key: "" });
  const saved = useRef(false);
  const assignees = useQuery({ queryKey: ["task-assignees", business, task ? "update" : "create"], queryFn: () => tasksApi.assignees(business, task ? "update" : "create") });
  const dirty = JSON.stringify(draft) !== JSON.stringify(initial);
  const change = (field: string, value: string) => setDraft(previous => ({ ...previous, [field]: value }));
  const save = useMutation({
    mutationFn: async () => {
      const payload: Record<string, unknown> = {};
      for (const [field, value] of Object.entries(draft)) {
        if (task && value === initial[field]) continue;
        if (links.includes(field as TaskRelationType) || field === "assignee") payload[field] = value ? Number(value) : null;
        else if (field === "due_at" || field === "reminder_at") payload[field] = taskDateISO(value, zone);
        else payload[field] = value.trim();
      }
      const signature = JSON.stringify({ payload, version: version?.updated_at });
      if (attempt.current.signature !== signature) attempt.current = { signature, key: crypto.randomUUID() };
      return task && version ? tasksApi.command({ task: version, action: "update-details", payload, key: attempt.current.key })
        : tasksApi.createWithKey({ ...payload, business } as TaskCreatePayload, attempt.current.key);
    },
    onSuccess: result => { saved.current = true; onSaved(result); },
  });
  const close = async () => {
    if (save.isPending) return;
    if (!dirty || (await confirm({ title: t("taskWorkspace.discardTitle"), confirmLabel: t("taskWorkspace.discard"), cancelLabel: t("taskWorkspace.keepEditing"), tone: "warning" })).confirmed) onClose();
  };
  const refresh = useMutation({
    mutationFn: () => tasksApi.getForBusiness(task!.id, business),
    onSuccess: current => { setVersion(current); save.reset(); },
  });
  const conflict = save.error && normalizeAppError(save.error).category === "conflict";
  const allowedLinks = links.filter(field => hasPermission(user, business, resources[field], "view"));
  return <Modal open title={t(task ? "taskWorkspace.edit" : "taskWorkspace.create")} onClose={() => void close()} size="lg" testId="task-editor">
    <TaskDraftGuard dirty={dirty || parentDirty} pending={save.isPending} saved={saved} />
    <form className="space-y-4" onSubmit={e => { e.preventDefault(); save.mutate(); }}>
      <Input autoFocus required maxLength={255} label={t("taskWorkspace.name")} value={draft.title} onChange={e => change("title", e.target.value)} />
      <div className="grid gap-4 sm:grid-cols-2">
        <Select label={t("taskWorkspace.assignee")} value={draft.assignee} disabled={assignees.isPending || Boolean(assignees.error)} onChange={e => change("assignee", e.target.value)} options={[
          { value: "", label: t("taskWorkspace.unassigned") },
          ...(draft.assignee && !assignees.data?.some(v => String(v.id) === draft.assignee) ? [{ value: draft.assignee, label: task?.assignee_name || user?.full_name || `#${draft.assignee}` }] : []),
          ...(assignees.data || []).map(v => ({ value: String(v.id), label: v.name })),
        ]} />
        <Input type="datetime-local" label={t("taskWorkspace.due")} value={draft.due_at} onChange={e => change("due_at", e.target.value)} />
      </div>
      {assignees.error ? <ErrorState error={assignees.error} action={<Button type="button" variant="secondary" onClick={() => void assignees.refetch()}>{t("taskWorkspace.refresh")}</Button>} /> : null}
      <p className="text-xs text-platforma-subtle">{t("taskWorkspace.zone", { zone })}</p>
      <Button type="button" variant="ghost" aria-expanded={more} onClick={() => setMore(!more)}>{t("taskWorkspace.more")}</Button>
      {more ? <div className="space-y-4 border-t border-platforma-border pt-4">
        <Textarea label={t("taskWorkspace.description")} value={draft.description} onChange={e => change("description", e.target.value)} rows={3} />
        <div className="grid gap-4 sm:grid-cols-2">
          <Select label={t("taskWorkspace.priority")} value={draft.priority} onChange={e => change("priority", e.target.value)} options={["low", "normal", "high", "urgent"].map(value => ({ value, label: t(`taskWorkspace.priority.${value}`) }))} />
          <Input type="datetime-local" label={t("taskWorkspace.reminder")} value={draft.reminder_at} onChange={e => change("reminder_at", e.target.value)} />
        </div>
        {allowedLinks.length ? <fieldset className="space-y-3">
          <legend className="mb-2 text-sm font-semibold">{t("taskWorkspace.links")}</legend>
          <Select aria-label={t("taskWorkspace.links")} value={relation} onChange={e => setRelation(e.target.value as TaskRelationType)} options={allowedLinks.map(value => ({ value, label: t(`taskWorkspace.link.${value}`) }))} />
          {allowedLinks.includes(relation) ? <TaskRelationPicker key={relation} type={relation} business={business} taskId={task?.id} value={draft[relation]} label={task?.relations?.find(v => v.type === relation)?.title} onChange={value => change(relation, value)} /> : null}
          <div className="flex flex-wrap gap-2">{links.filter(field => draft[field]).map(field => <span key={field} className="rounded-control bg-surface-muted px-2 py-1 text-xs">{t(`taskWorkspace.link.${field}`)} #{draft[field]}</span>)}</div>
        </fieldset> : null}
      </div> : null}
      {save.error ? <ErrorState error={save.error} message={conflict ? t("taskWorkspace.conflict") : undefined} action={conflict && task ? <Button type="button" variant="secondary" isLoading={refresh.isPending} onClick={() => refresh.mutate()}>{t("taskWorkspace.refresh")}</Button> : undefined} /> : null}
      {refresh.error ? <ErrorState error={refresh.error} /> : null}
      {save.error ? <FieldErrorSummary error={normalizeAppError(save.error)} fieldLabels={Object.fromEntries(Object.keys(draft).map(field => [field, t(`taskWorkspace.${field === "title" ? "name" : field === "due_at" ? "due" : field === "reminder_at" ? "reminder" : links.includes(field as TaskRelationType) ? `link.${field}` : field}`)]))} /> : null}
      <div className="flex justify-end gap-2 border-t border-platforma-border pt-4">
        <Button type="button" variant="secondary" disabled={save.isPending} onClick={() => void close()}>{t("common.cancel")}</Button>
        <Button type="submit" isLoading={save.isPending} disabled={!draft.title.trim() || Boolean(task && !dirty)}>{t("taskWorkspace.save")}</Button>
      </div>
    </form>
  </Modal>;
}

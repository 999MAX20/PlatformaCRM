import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight, Check, Clock, Eye, Maximize2, Pause, Pencil, Play, RotateCcw, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { activityEventsApi } from "../../../api/activities";
import { normalizeAppError } from "../../../api/appError";
import { tasksApi } from "../../../api/tasks";
import { useActionConfirm } from "../../../components/actions/ActionConfirmProvider";
import { ActionMenu, type ActionMenuItem } from "../../../components/ui/ActionMenu";
import { Badge } from "../../../components/ui/Badge";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Modal } from "../../../components/ui/Modal";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { Textarea } from "../../../components/ui/Textarea";
import { useI18n } from "../../../lib/i18n";
import { useBodyScrollLock } from "../../../hooks/useBodyScrollLock";
import type { Id, Task } from "../../../types";
import { taskDateISO, taskDateLabel, taskGroup } from "../workspaceUtils";
import { TaskEditor } from "./TaskEditor";
import { TaskStatus } from "./TaskStatus";
import { TaskDraftGuard } from "./TaskDraftGuard";

export function TaskInspector({ id, business, zone, expanded = false, returnTo = "/app/tasks", suspendGuard = false, onClose, onBusyChange }: {
  id: Id; business: Id; zone: string; expanded?: boolean; returnTo?: string; suspendGuard?: boolean; onClose: () => void; onBusyChange?: (busy: boolean) => void;
}) {
  const { t, language } = useI18n();
  const queryClient = useQueryClient();
  const confirm = useActionConfirm();
  const [tab, setTab] = useState("comments");
  const [comment, setComment] = useState("");
  const [editing, setEditing] = useState(false);
  const [dialog, setDialog] = useState<"wait" | "cancel" | "snooze" | null>(null);
  const [reason, setReason] = useState("");
  const [until, setUntil] = useState("");
  const [smallScreen, setSmallScreen] = useState(() => window.matchMedia("(max-width: 1279px)").matches);
  const mobileDialog = smallScreen && !expanded;
  useBodyScrollLock(mobileDialog);
  useEffect(() => {
    const media = window.matchMedia("(max-width: 1279px)");
    const changed = () => setSmallScreen(media.matches);
    media.addEventListener("change", changed);
    return () => media.removeEventListener("change", changed);
  }, []);
  const attempt = useRef<{ signature: string; key: string; task?: Task }>({ signature: "", key: "" });
  const heading = useRef<HTMLHeadingElement>(null);
  const taskQuery = useQuery({ queryKey: ["task", business, id], queryFn: () => tasksApi.getForBusiness(id, business) });
  const task = taskQuery.data;
  const comments = useQuery({ queryKey: ["task-comments", business, id], queryFn: () => tasksApi.comments(id), enabled: Boolean(task) && tab === "comments" });
  const history = useQuery({ queryKey: ["task-activity", business, id], queryFn: () => activityEventsApi.listForEntity({ entity_type: "Task", entity_id: id }), enabled: Boolean(task) && tab === "history" });
  const invalidate = async (updated?: Task) => {
    if (updated) queryClient.setQueryData(["task", business, id], updated);
    await Promise.all(["task", "tasks", "task-summary", "task-workload", "task-comments", "task-activity"].map(key => queryClient.invalidateQueries({ queryKey: [key] })));
  };
  const command = useMutation({
    mutationFn: async ({ action, payload = {} }: { action: string; payload?: Record<string, unknown> }) => {
      if (!task) throw new Error("Task unavailable");
      if (action === "wait") payload = { ...payload, waiting_until: taskDateISO(String(payload.waiting_until || ""), zone) };
      if (action === "snooze") payload = { ...payload, snoozed_until: taskDateISO(String(payload.snoozed_until || ""), zone) };
      const signature = JSON.stringify({ action, payload, id: task.id });
      if (attempt.current.signature !== signature) attempt.current = { signature, key: crypto.randomUUID(), task };
      return tasksApi.command({ task: attempt.current.task || task, action, payload, key: attempt.current.key });
    },
    onSuccess: async (result, variables) => {
      attempt.current = { signature: "", key: "" };
      if (variables.action === "add-comment") setComment("");
      setDialog(null); setReason(""); setUntil("");
      await invalidate(variables.action === "add-comment" ? undefined : result);
    },
  });
  useEffect(() => {
    onBusyChange?.(Boolean(comment.trim() || reason || until || editing || dialog || command.isPending));
    return () => onBusyChange?.(false);
  }, [comment, reason, until, editing, dialog, command.isPending, onBusyChange]);
  const close = async () => {
    if (command.isPending || editing || dialog) return;
    onClose();
  };
  useEffect(() => { heading.current?.focus(); }, [task?.id]);
  const openDialog = (value: "wait" | "cancel" | "snooze") => { command.reset(); setReason(""); setUntil(""); setDialog(value); };
  const closeDialog = async () => {
    if (command.isPending) return;
    if ((!reason && !until) || (await confirm({ title: t("taskWorkspace.discardTitle"), confirmLabel: t("taskWorkspace.discard"), cancelLabel: t("taskWorkspace.keepEditing"), tone: "warning" })).confirmed) { setDialog(null); setReason(""); setUntil(""); command.reset(); }
  };
  const allowed = (name: string) => task?.available_actions?.includes(name);
  const actionItems: ActionMenuItem[] = [
    { key: "wait", label: t("taskWorkspace.wait"), icon: Pause, onSelect: () => openDialog("wait") },
    { key: "snooze", label: t("taskWorkspace.snooze"), icon: Clock, onSelect: () => openDialog("snooze") },
    { key: "watch", label: t("taskWorkspace.watch"), icon: Eye, onSelect: () => command.mutate({ action: "add-watcher" }) },
    { key: "cancel", label: t("taskWorkspace.cancel"), icon: X, tone: "warning", onSelect: () => openDialog("cancel") },
  ].filter(item => allowed(item.key)) as ActionMenuItem[];
  const format = (value?: string | null) => taskDateLabel(value, zone, language);
  const conflict = command.error && normalizeAppError(command.error).category === "conflict";
  return <aside data-testid="task-inspector" role={mobileDialog ? "dialog" : undefined} aria-modal={mobileDialog || undefined} aria-label={task?.title || t("tasks.title")}
    onKeyDown={e => {
      if (editing || dialog || (mobileDialog && document.querySelectorAll('[role="dialog"][aria-modal="true"]').length > 1)) return;
      if (e.key === "Escape") { e.stopPropagation(); void close(); }
      if (e.key === "Tab" && mobileDialog) {
        const targets = Array.from(e.currentTarget.querySelectorAll<HTMLElement>('a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), [tabindex="0"]')).filter(item => item.getClientRects().length);
        const first = targets[0], last = targets.at(-1);
        if (e.shiftKey && (document.activeElement === first || document.activeElement === heading.current)) { e.preventDefault(); last?.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus(); }
      }
    }}
    className={expanded ? "mx-auto w-full max-w-4xl overflow-hidden rounded-card border border-platforma-border bg-surface-card" : "fixed inset-0 z-[var(--platforma-z-drawer)] flex flex-col bg-surface-card xl:sticky xl:top-4 xl:z-auto xl:h-[calc(100dvh-112px)] xl:min-h-[560px] xl:w-[580px] xl:rounded-card xl:border xl:border-platforma-border"}>
    {!editing && !suspendGuard ? <TaskDraftGuard dirty={Boolean(comment.trim() || reason || until)} pending={command.isPending} /> : null}
    <header className="flex items-center justify-between border-b border-platforma-border px-5 py-3">
      <span className="text-xs font-medium text-platforma-subtle">#{id}</span>
      <div className="flex items-center gap-1">
        {!expanded ? <Link aria-label={t("taskWorkspace.expand")} to={`/app/tasks/${id}`} state={{ returnTo }} className="grid h-11 w-11 place-items-center rounded-control text-platforma-subtle hover:bg-surface-hover focus-visible:ring-2 focus-visible:ring-brand-500"><Maximize2 size={18} /></Link> : null}
        <Button variant="ghost" size="icon" className="h-11 w-11" aria-label={t(expanded ? "taskWorkspace.back" : "taskWorkspace.close")} onClick={() => void close()}><X size={20} /></Button>
      </div>
    </header>
    <div className="min-h-0 flex-1 space-y-6 overflow-y-auto p-5 pb-8 sm:p-6">
      {taskQuery.isPending ? <LoadingState /> : taskQuery.error ? <ErrorState error={taskQuery.error} action={<Button variant="secondary" onClick={() => void taskQuery.refetch()}>{t("taskWorkspace.refresh")}</Button>} /> : task ? <>
        <div className="space-y-3">
          <div className="flex flex-wrap gap-2"><TaskStatus status={task.status} />{taskGroup(task, zone) === "overdue" ? <Badge size="sm" variant="danger">{t("taskWorkspace.overdue")}</Badge> : null}</div>
          <h2 ref={heading} tabIndex={-1} className="break-words text-[22px] font-bold leading-[30px] outline-none">{task.title}</h2>
          <div className="flex flex-wrap gap-2">
            {allowed("complete") ? <Button disabled={command.isPending} onClick={() => command.mutate({ action: "complete" })}><Check size={17} />{t("taskWorkspace.complete")}</Button> : null}
            {(["start", "resume", "reopen"] as const).filter(allowed).map(action => <Button key={action} variant="secondary" disabled={command.isPending} onClick={() => command.mutate({ action })}>{action === "reopen" ? <RotateCcw size={17} /> : <Play size={17} />}{t(`taskWorkspace.${action}`)}</Button>)}
            {allowed("edit") ? <Button variant="secondary" aria-label={t("taskWorkspace.edit")} onClick={() => setEditing(true)}><Pencil size={17} /></Button> : null}
            {actionItems.length ? <ActionMenu label={t("taskWorkspace.actions")} overlay={mobileDialog ? "drawer" : undefined} items={actionItems} disabled={command.isPending} /> : null}
          </div>
        </div>
        {command.error && !dialog ? <ErrorState error={command.error} message={conflict ? t("taskWorkspace.conflict") : undefined} action={conflict ? <Button variant="secondary" onClick={async () => { await taskQuery.refetch(); attempt.current = { signature: "", key: "" }; command.reset(); }}>{t("taskWorkspace.refresh")}</Button> : undefined} /> : null}
        <dl className="grid grid-cols-[minmax(100px,0.75fr)_minmax(0,1.25fr)] gap-x-4 gap-y-3 text-sm">
          {[ ["assignee", task.assignee_name || t("taskWorkspace.unassigned")], ["due", format(task.due_at)], ["priority", t(`taskWorkspace.priority.${task.priority}`)], ["reminder", format(task.reminder_at)], ["creator", task.created_by_name || "—"] ].map(([name, value]) => <div key={name} className="contents"><dt className="text-platforma-subtle">{t(`taskWorkspace.${name}`)}</dt><dd className="break-words font-medium">{value}</dd></div>)}
        </dl>
        {task.status === "waiting" ? <div className="space-y-1 border-l-2 border-platforma-warning pl-3 text-sm"><p className="font-semibold">{t("taskWorkspace.waitingReason")}</p><p className="whitespace-pre-wrap break-words">{task.waiting_reason}</p>{task.waiting_until ? <p className="text-platforma-subtle">{t("taskWorkspace.waitingUntil")}: {format(task.waiting_until)}</p> : null}</div> : null}
        {task.snoozed_until && new Date(task.snoozed_until) > new Date() ? <p className="text-sm text-platforma-subtle">{t("taskWorkspace.snoozedUntil")}: {format(task.snoozed_until)}</p> : null}
        {task.status === "cancelled" ? <p className="whitespace-pre-wrap text-sm"><strong>{t("taskWorkspace.cancelReason")}: </strong>{task.cancel_reason}</p> : null}
        <section className="space-y-2 border-t border-platforma-border pt-5"><h3 className="text-base font-semibold">{t("taskWorkspace.description")}</h3><p className="whitespace-pre-wrap break-words text-sm leading-[22px] text-platforma-subtle">{task.description || t("taskWorkspace.noDescription")}</p></section>
        <section className="space-y-2 border-t border-platforma-border pt-5"><h3 className="text-base font-semibold">{t("taskWorkspace.links")}</h3>
          {task.relations?.length ? task.relations.map(link => <Link key={link.type} to={link.href} className="flex min-h-11 items-center gap-3 rounded-control px-2 text-sm hover:bg-surface-hover focus-visible:ring-2 focus-visible:ring-brand-500"><span className="w-28 shrink-0 text-platforma-subtle">{t(`taskWorkspace.link.${link.type}`)}</span><span className="min-w-0 flex-1 break-words font-medium">{link.title}{link.at ? <span className="block text-xs text-platforma-subtle">{format(link.at)}</span> : null}</span><ArrowUpRight size={16} className="shrink-0 text-platforma-subtle" /></Link>) : <p className="text-sm text-platforma-subtle">{t("taskWorkspace.noLinks")}</p>}
        </section>
        <section className="space-y-4 border-t border-platforma-border pt-4">
          <div role="tablist" className="flex gap-5 border-b border-platforma-border">{["comments", "history"].map(value => <button key={value} role="tab" aria-selected={tab === value} className={`min-h-11 border-b-2 text-sm font-semibold ${tab === value ? "border-brand-500 text-brand-700" : "border-transparent text-platforma-subtle"}`} onClick={() => setTab(value)}>{t(`taskWorkspace.${value}`)}</button>)}</div>
          {tab === "comments" ? <>
            {comments.isPending ? <LoadingState /> : comments.error ? <ErrorState error={comments.error} action={<Button variant="secondary" onClick={() => void comments.refetch()}>{t("taskWorkspace.refresh")}</Button>} /> : comments.data?.length ? comments.data.map(item => <article key={item.id} className="space-y-1 text-sm"><div className="flex flex-wrap justify-between gap-1"><strong>{item.author_name || item.author_email || "—"}</strong><time className="text-xs text-platforma-subtle">{format(item.created_at)}</time></div><p className="whitespace-pre-wrap break-words leading-[22px]">{item.text}</p></article>) : <p className="text-sm text-platforma-subtle">{t("taskWorkspace.noComments")}</p>}
            {allowed("comment") ? <form className="space-y-2" onSubmit={e => { e.preventDefault(); command.mutate({ action: "add-comment", payload: { text: comment.trim() } }); }}><Textarea label={t("taskWorkspace.comment")} value={comment} onChange={e => setComment(e.target.value)} rows={3} /><div className="flex justify-end"><Button type="submit" disabled={!comment.trim()} isLoading={command.isPending}>{t("taskWorkspace.send")}</Button></div></form> : null}
          </> : history.isPending ? <LoadingState /> : history.error ? <ErrorState error={history.error} action={<Button variant="secondary" onClick={() => void history.refetch()}>{t("taskWorkspace.refresh")}</Button>} /> : history.data?.length ? history.data.map(event => <article key={event.id} className="border-l border-platforma-border pl-3 text-sm"><p className="whitespace-pre-wrap break-words">{event.text}</p><time className="text-xs text-platforma-subtle">{format(event.created_at)}</time></article>) : <p className="text-sm text-platforma-subtle">{t("taskWorkspace.noHistory")}</p>}
        </section>
      </> : null}
    </div>
    {editing && task ? <TaskEditor task={task} parentDirty={Boolean(comment.trim())} business={business} zone={zone} onClose={() => setEditing(false)} onSaved={updated => { setEditing(false); void invalidate(updated); }} /> : null}
    {dialog ? <Modal open title={t(`taskWorkspace.${dialog}`)} onClose={() => void closeDialog()} size="sm"><form className="space-y-4" onSubmit={e => { e.preventDefault(); command.mutate({ action: dialog, payload: dialog === "snooze" ? { snoozed_until: until } : { reason: reason.trim(), ...(dialog === "wait" ? { waiting_until: until } : {}) } }); }}>
      {dialog !== "snooze" ? <Textarea required minLength={3} label={t(dialog === "wait" ? "taskWorkspace.waitingReason" : "taskWorkspace.cancelReason")} value={reason} onChange={e => setReason(e.target.value)} autoFocus /> : null}
      {dialog !== "cancel" ? <><Input type="datetime-local" required={dialog === "snooze"} label={t(dialog === "wait" ? "taskWorkspace.waitingUntil" : "taskWorkspace.snoozedUntil")} value={until} onChange={e => setUntil(e.target.value)} /><p className="text-xs text-platforma-subtle">{t("taskWorkspace.zone", { zone })}</p></> : null}
      {command.error ? <ErrorState error={command.error} message={conflict ? t("taskWorkspace.conflict") : undefined} action={conflict ? <Button type="button" variant="secondary" onClick={async () => { await taskQuery.refetch(); attempt.current = { signature: "", key: "" }; command.reset(); }}>{t("taskWorkspace.refresh")}</Button> : undefined} /> : null}
      <div className="flex justify-end gap-2"><Button type="button" variant="secondary" disabled={command.isPending} onClick={() => void closeDialog()}>{t("common.cancel")}</Button><Button type="submit" variant={dialog === "cancel" ? "warning" : "primary"} isLoading={command.isPending} disabled={dialog !== "snooze" ? reason.trim().length < 3 : !until}>{t("taskWorkspace.save")}</Button></div>
    </form></Modal> : null}
  </aside>;
}

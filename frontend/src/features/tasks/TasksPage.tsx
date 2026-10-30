import { useInfiniteQuery, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, List, MessageSquare, Plus, SlidersHorizontal, Users } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router";
import { tasksApi } from "../../api/tasks";
import { taskWorkspaceParams, taskWorkspaceQuery } from "./taskWorkspaceQueries";
import { usePageHeader } from "../../components/layout/PageHeaderContext";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { EmptyState, ErrorState, ForbiddenState, LoadingState } from "../../components/ui/StateViews";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useClientCreateIntent } from "../../hooks/useClientCreateIntent";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";
import { useI18n } from "../../lib/i18n";
import { hasPermission } from "../../lib/permissions";
import type { Client, Id } from "../../types";
import { useAuth } from "../auth/AuthProvider";
import { TaskEditor } from "./components/TaskEditor";
import { TaskInspector } from "./components/TaskInspector";
import { TaskStatus } from "./components/TaskStatus";
import { taskDateLabel, taskGroup } from "./workspaceUtils";

export function TasksPage() {
  const { business, isLoading, error } = useActiveBusiness();
  return business ? <TaskQueue key={business.id} business={business.id} zone={business.timezone || "UTC"} /> : isLoading ? <LoadingState /> : error ? <ErrorState error={error} /> : <ForbiddenState />;
}

function TaskQueue({ business, zone }: { business: Id; zone: string }) {
  const { t, language } = useI18n();
  const { user } = useAuth();
  const { setPageHeader } = usePageHeader();
  const queryClient = useQueryClient();
  const [params, setParams] = useSearchParams();
  const [creating, setCreating] = useState(false);
  const [inspectorBusy, setInspectorBusy] = useState(false);
  const [initialClient, setInitialClient] = useState<Id>();
  const [filters, setFilters] = useState(false);
  const scope = params.get("tab") || "my";
  const bucket = params.get("bucket") || "active";
  const view = params.get("view") || "list";
  const selected = Number(params.get("task")) || null;
  const search = params.get("search") || "";
  const debouncedSearch = useDebouncedValue(search, 250);
  const canCreate = hasPermission(user, business, "tasks", "create");
  const canUpdate = hasPermission(user, business, "tasks", "update");
  const canTeam = hasPermission(user, business, "team", "view");
  const openCreate = useCallback(() => { setInitialClient(undefined); setCreating(true); }, []);
  const openLinked = useCallback((client: Client | null) => { setInitialClient(client?.id); setCreating(true); }, []);
  const context = useClientCreateIntent({ businessId: business, allowed: canCreate, onOpen: openLinked });
  const update = (key: string, value: string) => setParams(previous => {
    const next = new URLSearchParams(previous);
    if (value) next.set(key, value); else next.delete(key);
    return next;
  }, { replace: true, preventScrollReset: true });
  const { base, list: listParams } = taskWorkspaceParams(business, params, debouncedSearch);
  const list = useInfiniteQuery(taskWorkspaceQuery(listParams));
  const summary = useQuery({ queryKey: ["task-summary", base], queryFn: () => tasksApi.summary(base) });
  const team = useQuery({ queryKey: ["task-workload", base], queryFn: () => tasksApi.workload({ ...base, business }), enabled: view === "team" && canTeam });
  const assignees = useQuery({ queryKey: ["task-assignees", business], queryFn: () => tasksApi.assignees(business), enabled: filters && canUpdate });
  useEffect(() => {
    setPageHeader({ title: t("tasks.title"), primaryAction: canCreate ? { label: t("taskWorkspace.create"), icon: Plus, onClick: openCreate, disabled: inspectorBusy, showOnMobile: true, focusReturnId: "task-create-trigger" } : undefined });
    return () => setPageHeader(null);
  }, [canCreate, inspectorBusy, openCreate, setPageHeader, t]);
  const tasks = list.data?.pages.flatMap(page => page.results) || [];
  const groups = ["overdue", "today", "later", "noDue", "done", "cancelled"];
  const hasFilters = Boolean(search || params.get("priority") || params.get("assignee") || params.get("status") || bucket !== "active");
  const reset = () => setParams({ tab: scope }, { replace: true, preventScrollReset: true });
  const close = () => { const id = selected; update("task", ""); requestAnimationFrame(() => document.getElementById(`task-row-${id}`)?.focus({ preventScroll: true })); };
  return <div data-testid="tasks-workspace-ready" className="mx-auto w-full max-w-[1760px] p-4 sm:p-6">
    <div className={`grid items-start gap-4 ${selected ? "xl:grid-cols-[minmax(0,1fr)_580px]" : "grid-cols-1"}`}>
      <main className="min-w-0 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-1 rounded-control bg-surface-muted p-1" aria-label={t("tasks.title")}>{["my", "all"].map(value => <Button key={value} variant={scope === value ? "secondary" : "ghost"} className="min-h-11" aria-pressed={scope === value} onClick={() => update("tab", value)}>{t(`taskWorkspace.${value}`)}</Button>)}</div>
          {canTeam ? <div className="flex gap-1"><Button variant={view === "list" ? "secondary" : "ghost"} aria-label={t("taskWorkspace.list")} aria-pressed={view === "list"} onClick={() => update("view", "list")}><List size={17} /></Button><Button variant={view === "team" ? "secondary" : "ghost"} aria-label={t("taskWorkspace.team")} aria-pressed={view === "team"} onClick={() => update("view", "team")}><Users size={17} /></Button></div> : null}
        </div>
        <div className="rounded-card border border-platforma-border bg-surface-card">
          <div className="space-y-3 border-b border-platforma-border p-4">
            <div className="flex items-center gap-2"><div className="min-w-0 flex-1"><Input aria-label={t("taskWorkspace.search")} placeholder={t("taskWorkspace.search")} value={search} onChange={e => update("search", e.target.value)} /></div><Button variant="secondary" aria-expanded={filters} aria-label={t("taskWorkspace.filters")} onClick={() => setFilters(!filters)}><SlidersHorizontal size={17} /></Button></div>
            <div hidden={view === "team" && canTeam} className="flex flex-wrap gap-1">{["active", "overdue", "today", "noDue", "done", "cancelled"].map(value => <button key={value} aria-pressed={bucket === value} onClick={() => update("bucket", value)} className={`flex min-h-11 items-center gap-2 rounded-control px-3 text-[13px] font-semibold focus-visible:ring-2 focus-visible:ring-brand-500 ${bucket === value ? "bg-brand-50 text-brand-700" : "text-platforma-subtle hover:bg-surface-hover"}`}>
              {t(`taskWorkspace.${value}`)}{summary.data ? <span className="text-xs tabular-nums">{summary.data[value as keyof typeof summary.data]}</span> : null}
            </button>)}</div>
            {summary.error ? <ErrorState error={summary.error} action={<Button variant="secondary" onClick={() => void summary.refetch()}>{t("taskWorkspace.refresh")}</Button>} /> : null}
            {filters ? <div className="grid gap-3 border-t border-platforma-border pt-3 sm:grid-cols-2">
              <Select aria-label={t("taskWorkspace.filters")} value={scope} onChange={e => update("tab", e.target.value)} options={["my", "all", "created", "watching"].map(value => ({ value, label: t(`taskWorkspace.${value}`) }))} />
              <Select aria-label={t("taskWorkspace.priority")} value={params.get("priority") || ""} onChange={e => update("priority", e.target.value)} options={[{ value: "", label: t("taskWorkspace.allPriorities") }, ...["low", "normal", "high", "urgent"].map(value => ({ value, label: t(`taskWorkspace.priority.${value}`) }))]} />
              <Select aria-label={t("taskWorkspace.allStatuses")} value={params.get("status") || ""} onChange={e => update("status", e.target.value)} options={[{ value: "", label: t("taskWorkspace.allStatuses") }, ...["open", "in_progress", "waiting"].map(value => ({ value, label: t(`taskWorkspace.status.${value}`) }))]} />
              {canUpdate ? <Select aria-label={t("taskWorkspace.assignee")} value={params.get("assignee") || ""} onChange={e => update("assignee", e.target.value)} options={[{ value: "", label: t("taskWorkspace.allAssignees") }, { value: "unassigned", label: t("taskWorkspace.unassigned") }, ...(assignees.data || []).map(v => ({ value: String(v.id), label: v.name }))]} /> : null}
              {assignees.error ? <ErrorState error={assignees.error} /> : null}
            </div> : null}
          </div>
          {context.error ? <ErrorState message={context.error} /> : null}
          {view === "team" && canTeam ? <div className="p-4">
            {team.isPending ? <LoadingState /> : team.error ? <ErrorState error={team.error} action={<Button variant="secondary" onClick={() => void team.refetch()}>{t("taskWorkspace.refresh")}</Button>} /> : !team.data?.items.length ? <EmptyState title={t("taskWorkspace.empty")} /> : <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr className="border-b border-platforma-border text-xs text-platforma-subtle">{["assignee", "active", "overdue", "today"].map(key => <th key={key} className="px-3 py-3 font-medium">{t(`taskWorkspace.${key}`)}</th>)}</tr></thead><tbody>{team.data.items.map(item => <tr key={item.user_id || "unassigned"} className="border-b border-platforma-border last:border-0"><td className="px-3 py-3"><button className="min-h-11 text-left font-semibold hover:text-brand-700" onClick={() => { setParams(previous => { const next = new URLSearchParams(previous); next.set("view", "list"); next.set("bucket", "active"); next.delete("status"); next.set("assignee", String(item.user_id || "unassigned")); return next; }, { replace: true }); }}>{item.user_id ? item.name : t("taskWorkspace.unassigned")}</button></td><td className="px-3 tabular-nums">{item.total}</td><td className="px-3 tabular-nums">{item.overdue}</td><td className="px-3 tabular-nums">{item.due_today}</td></tr>)}</tbody></table></div>}
          </div> : list.isPending ? <div className="p-6"><LoadingState /></div> : list.error ? <ErrorState error={list.error} action={<Button variant="secondary" onClick={() => void list.refetch()}>{t("taskWorkspace.refresh")}</Button>} /> : !tasks.length ? <div className="p-6"><EmptyState title={t(hasFilters ? "taskWorkspace.noResults" : "taskWorkspace.empty")} action={hasFilters ? <Button variant="secondary" onClick={reset}>{t("taskWorkspace.reset")}</Button> : undefined} /></div> : <div>
            {groups.map(group => {
              const rows = tasks.filter(task => taskGroup(task, zone) === group);
              return rows.length ? <section key={group} aria-label={t(`taskWorkspace.${group}`)}>
                <h2 className={`border-b border-platforma-border bg-surface-muted/60 px-4 py-2.5 text-xs font-semibold ${group === "overdue" ? "text-platforma-danger" : "text-platforma-subtle"}`}>{t(`taskWorkspace.${group}`)}</h2>
                {rows.map(task => <button key={task.id} id={`task-row-${task.id}`} data-testid="task-row" aria-pressed={selected === task.id} onClick={() => update("task", String(task.id))} className={`group flex w-full items-start gap-3 border-b border-platforma-border px-4 py-4 text-left last:border-b-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-500 ${selected === task.id ? "bg-brand-50" : "hover:bg-surface-hover"}`}>
                  <span className={`mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full border ${task.status === "done" ? "border-brand-500 bg-brand-500 text-white" : "border-platforma-control"}`}>{task.status === "done" ? <Check size={13} /> : null}</span>
                  <span className="min-w-0 flex-1 space-y-2"><span className="block break-words text-sm font-semibold leading-5">{task.title}</span><span className="flex flex-wrap items-center gap-x-3 gap-y-2"><TaskStatus status={task.status} />{task.priority === "high" || task.priority === "urgent" ? <span className="text-xs font-medium text-platforma-warning">{t(`taskWorkspace.priority.${task.priority}`)}</span> : null}<span className={`text-xs ${group === "overdue" ? "text-platforma-danger" : "text-platforma-subtle"}`}>{task.due_at ? taskDateLabel(task.due_at, zone, language) : t("taskWorkspace.noDue")}</span>{task.comments_count ? <span className="flex items-center gap-1 text-xs text-platforma-subtle"><MessageSquare size={13} />{task.comments_count}</span> : null}</span>{task.relations?.length ? <span className="block truncate text-xs text-platforma-subtle">{task.relations.map(link => `${t(`taskWorkspace.link.${link.type}`)}: ${link.title}`).join(" · ")}</span> : null}</span>
                  <span className="hidden max-w-32 truncate pt-0.5 text-xs text-platforma-subtle sm:block">{task.assignee_name || t("taskWorkspace.unassigned")}</span>
                </button>)}
              </section> : null;
            })}
            <div className="flex flex-wrap items-center justify-between gap-3 p-4 text-xs text-platforma-subtle"><span>{t("taskWorkspace.count", { count: list.data?.pages[0]?.count || 0 })}</span>{list.hasNextPage ? <Button variant="secondary" isLoading={list.isFetchingNextPage} onClick={() => void list.fetchNextPage()}>{t("taskWorkspace.loadMore")}</Button> : null}</div>
          </div>}
        </div>
      </main>
      {selected ? <TaskInspector key={`${business}:${selected}`} id={selected} business={business} zone={zone} returnTo={`/app/tasks?${params}`} suspendGuard={creating} onBusyChange={setInspectorBusy} onClose={close} /> : null}
    </div>
    {creating ? <TaskEditor business={business} zone={zone} initialClient={initialClient} onClose={() => setCreating(false)} onSaved={task => { setCreating(false); update("task", String(task.id)); void Promise.all(["tasks", "task-summary", "task-workload"].map(key => queryClient.invalidateQueries({ queryKey: [key] }))); }} /> : null}
  </div>;
}

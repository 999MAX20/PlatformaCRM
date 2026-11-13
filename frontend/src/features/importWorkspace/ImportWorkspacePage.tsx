import { ImportErrorNotice } from "./ImportErrorNotice";
import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useBlocker, useSearchParams } from "react-router";
import { ArrowLeft, Plus, Upload } from "lucide-react";
import { importWorkspaceApi, importEntities, type ImportWorkspace, type ImportSource, type ImportEntity } from "../../api/importWorkspace";
import { getApiErrorMessage } from "../../api/client";
import { normalizeAppError } from "../../api/appError";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Select } from "../../components/ui/Select";
import { Modal } from "../../components/ui/Modal";
import { EmptyState, ForbiddenState, LoadingState } from "../../components/ui/StateViews";
import { usePageLoading } from "../../components/ui/PageLoadingBoundary";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useI18n } from "../../lib/i18n";
import { hasPermission } from "../../lib/permissions";
import { useAuth } from "../auth/AuthProvider";
import { SourceMapping } from "./SourceMapping";
import { SourceRows } from "./SourceRows";
import { ImportPreview } from "./ImportPreview";
import { ImportProfiles, ImportActivationAction } from "./ImportActions";

export function ImportWorkspacePage() {
  const { business, isLoading } = useActiveBusiness(); const { user } = useAuth();
  const { t } = useI18n();
  if (isLoading) return <LoadingState scope="page" />;
  if (!business) return <EmptyState title={t("integrations.page.noBusinessTitle")} />;
  if (!hasPermission(user, business.id, "integrations", "manage")) return <ForbiddenState />;
  return <WorkspacePage key={`${user?.id}:${business.id}`} businessId={business.id} timezone={business.timezone || "UTC"} />;
}

function WorkspacePage({ businessId, timezone }: { businessId: number; timezone: string }) {
  const { user } = useAuth();
  const { t, language } = useI18n(); const label = (key: string) => t(`importWorkspace.${key}`);
  const [params, setParams] = useSearchParams(); const id = Number(params.get("draft")) || null;
  const cache = useQueryClient(); const [requestBusy, setBusy] = useState(false); const [error, setError] = useState<unknown>(null);
  const [dirty, setDirty] = useState(false); const [selectedSource, setSelectedSource] = useState<number | null>(null);
  const [step, setStep] = useState<"fields" | "data" | "preview">("fields"); const [focusRow, setFocusRow] = useState<number>();
  const [entity, setEntity] = useState<ImportEntity>("clients"); const [dialog, setDialog] = useState<"confirm" | "cancel" | null>(null);
  const [historyPage, setHistoryPage] = useState(1); const uploadRef = useRef<HTMLInputElement>(null);
  const uploadMode = useRef<"new" | "append">("new");
  const requestPending = useRef(false);
  const workspace = useQuery({ queryKey: ["import-workspace", businessId, user?.id, id], queryFn: () => importWorkspaceApi.get(id!), enabled: !!id, refetchInterval: query => ["pending", "running"].includes(query.state.data?.operation?.status || "") ? 2000 : false });
  const history = useQuery({ queryKey: ["import-workspaces", businessId, user?.id, historyPage], queryFn: () => importWorkspaceApi.list(businessId, historyPage) });
  const data = !workspace.isError && workspace.data?.business === businessId ? workspace.data : undefined;
  usePageLoading(workspace.isLoading || history.isLoading);
  const operationBusy = ["pending", "running"].includes(data?.operation?.status || "");
  const busy = requestBusy || operationBusy;
  const canRefresh = Boolean(workspace.error || history.error || (error && id && ["conflict", "temporary", "offline", "internal"].includes(normalizeAppError(error).category)));
  useEffect(() => {
    if (data?.operation?.status === "succeeded" && data.operation.action === "preview") setStep("preview");
  }, [data?.operation?.id, data?.operation?.status, data?.operation?.action]);
  const source = data?.sources.find(item => item.id === selectedSource) || data?.sources[0];
  const editable = data?.state === "draft" || data?.state === "ready";
  const internalNavigation = useRef(false);
  const blocker = useBlocker(() => !internalNavigation.current && (dirty || requestBusy));
  useEffect(() => {
    if (!dirty && !requestBusy) return;
    const prevent = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", prevent); return () => window.removeEventListener("beforeunload", prevent);
  }, [dirty, requestBusy]);
  const accept = (next: ImportWorkspace) => {
    setFocusRow(undefined);
    cache.setQueryData(["import-workspace", businessId, user?.id, next.id], next);
    void cache.invalidateQueries({ queryKey: ["import-workspaces", businessId] });
    if (id !== next.id) {
      internalNavigation.current = true;
      setParams({ draft: String(next.id) });
      queueMicrotask(() => { internalNavigation.current = false; });
    }
  };
  const run = async (operation: () => Promise<ImportWorkspace>) => {
    if (busy || requestPending.current) return;
    requestPending.current = true;
    setBusy(true); setError(null);
    try { const next = await operation(); accept(next); return next; }
    catch (failure) { setError(failure); return undefined; }
    finally { requestPending.current = false; setBusy(false); }
  };
  const upload = async (files: File[]) => {
    const isNew = uploadMode.current === "new";
    if (!files.length || (!isNew && !data)) return;
    await run(async () => {
      let current = isNew ? await importWorkspaceApi.create(businessId) : data!;
      if (isNew) {
        setSelectedSource(null); setStep("fields"); setEntity("clients");
        accept(current);
      }
      for (const file of files) {
        current = await importWorkspaceApi.upload(current.id, current.version, file, isNew ? "clients" : entity);
        accept(current);
      }
      return current;
    });
  };
  return <main className="mx-auto w-full max-w-[1440px] space-y-4 py-4">
    <input ref={uploadRef} hidden type="file" accept=".csv,.xlsx" multiple disabled={dirty || busy} aria-label={label("upload")} onChange={event => { const files = Array.from(event.target.files || []); event.target.value = ""; void upload(files); }} />
    <header className="flex flex-wrap items-center justify-between gap-3"><div className="flex items-center gap-3"><Link to="/app/integrations" aria-label={t("nav.integrations")} className="rounded-control p-2 text-platforma-muted hover:bg-surface-hover"><ArrowLeft size={20} /></Link><h1 className="text-xl font-semibold text-platforma-text">{label("title")}</h1></div><Button disabled={dirty || busy} onClick={() => { uploadMode.current = "new"; uploadRef.current?.click(); }}><Plus size={16} />{label("new")}</Button></header>
    {(error || workspace.error || history.error) && <ImportErrorNotice error={error || workspace.error || history.error} message={getApiErrorMessage(error || workspace.error || history.error)} action={canRefresh ? <Button size="sm" variant="secondary" disabled={busy || dirty} onClick={() => { setError(null); if (id) void workspace.refetch(); void history.refetch(); }}>{label("reload")}</Button> : undefined} />}
    {requestBusy && <LoadingState label={label("processing")} />}
    {operationBusy && <div role="status" className="flex flex-wrap items-center gap-3 rounded-control border border-platforma-border bg-surface-card p-3 text-sm"><span>{label(`operation.${data?.operation.action}`)} · {data?.operation.total_rows} {label("rowsCount")}</span><Button variant="secondary" size="sm" disabled={requestBusy} onClick={async () => {
      if (!data) return;
      setBusy(true); setError(null);
      try { accept(await (data.operation.action === "confirm" ? importWorkspaceApi.confirm(data.id, data.version) : importWorkspaceApi.preview(data.id, data.version))); } catch (failure) { setError(failure); } finally { setBusy(false); }
    }}>{label("resumeOperation")}</Button></div>}
    {data?.operation.status === "failed" && <ImportErrorNotice error={data.operation} message={label(`operationError.${data.operation.error || "operation_failed"}`)} />}
    <div className="grid gap-4 xl:grid-cols-[240px_minmax(0,1fr)]">
      <Card padding="md" className="self-start"><h2 className="mb-3 text-sm font-semibold">{label("history")}</h2><div className="max-h-64 space-y-1 overflow-auto xl:max-h-[60vh]">{(!history.isError ? history.data?.results : [])?.map(item => <Button key={item.id} size="sm" variant={item.id === id ? "secondary" : "ghost"} className="w-full justify-between" disabled={dirty || busy} onClick={() => { setParams({ draft: String(item.id) }); setSelectedSource(null); setStep("fields"); setError(null); }}><span>{new Intl.DateTimeFormat(language, { dateStyle: "short", timeStyle: "short" }).format(new Date(item.created_at))}</span><span className="text-xs">{label(item.state)}</span></Button>)}</div>{(history.data?.count || 0) > 20 && <div className="mt-3 flex gap-2"><Button size="sm" variant="ghost" disabled={historyPage === 1 || dirty || busy} onClick={() => setHistoryPage(historyPage - 1)}>{label("previous")}</Button><Button size="sm" variant="ghost" disabled={historyPage * 20 >= (history.data?.count || 0) || dirty || busy} onClick={() => setHistoryPage(historyPage + 1)}>{label("next")}</Button></div>}</Card>
      <div className="min-w-0 space-y-4">
        {workspace.isLoading && id ? <LoadingState /> : !data ? <EmptyState title={label("empty")} /> : <>
          <div className="flex flex-wrap items-center gap-2"><span className="text-sm font-semibold">{label(data.state)}</span>{editable && <Button size="sm" variant="ghost" disabled={busy || dirty} onClick={() => setDialog("cancel")}>{label("cancel")}</Button>}</div>
          {editable && <Card padding="md"><div className="flex flex-wrap items-end gap-3"><Select label={label("entity")} value={entity} disabled={busy || dirty} options={importEntities.map(value => ({ value, label: label(value) }))} onChange={event => setEntity(event.target.value as ImportEntity)} /><Button variant="secondary" disabled={busy || dirty} onClick={() => { uploadMode.current = "append"; uploadRef.current?.click(); }}><Upload size={16} />{label("upload")}</Button></div><p className="mt-2 text-xs text-platforma-muted">{label("uploadHint")}</p></Card>}
          {data.sources.length > 0 && <>
            {editable && <nav aria-label={label("sources")} className="flex gap-2 overflow-x-auto pb-1">{data.sources.map(item => <Button key={item.id} size="sm" variant={source?.id === item.id ? "primary" : "secondary"} disabled={busy || dirty} onClick={() => { setSelectedSource(item.id); setFocusRow(undefined); }}>{item.filename}{item.sheet_name ? ` · ${item.sheet_name}` : ""} · {label(item.entity_type)}</Button>)}</nav>}
            {editable && <div className="flex flex-wrap gap-2">{(["fields", "data", "preview"] as const).map(item => <Button key={item} size="sm" variant={step === item ? "secondary" : "ghost"} disabled={busy || (item === "preview" && (dirty || !data.report.rows))} onClick={() => setStep(item)}>{label(item)}</Button>)}</div>}
            {editable && source && step === "fields" && <ImportProfiles workspace={data} sourceId={source.id} disabled={busy || dirty} run={run} />}
            {editable && source && step !== "preview" && <SourceEditor key={`${data.id}:${source.id}:${data.version}`} source={source} workspace={data} step={step} focusRow={focusRow} busy={busy} onDirty={setDirty} onSave={next => run(() => importWorkspaceApi.saveSource(data.id, data.version, next))} onDuplicate={kind => run(() => importWorkspaceApi.duplicate(data.id, data.version, source.id, kind))} onRemove={() => run(() => importWorkspaceApi.removeSource(data.id, data.version, source.id))} />}
            {(step === "preview" || data.state === "imported") && <ImportPreview key={`${data.id}:${data.version}`} workspace={data} timezone={timezone} onEdit={(sourceId, row) => { setSelectedSource(sourceId); setFocusRow(row); setStep("data"); }} />}
            {data.state === "imported" && <ImportActivationAction key={data.id} workspace={data} timezone={timezone} onBusy={setBusy} />}
            {editable && <div className="flex flex-wrap items-center justify-between gap-3 border-t border-platforma-border pt-4"><p className="max-w-xl text-sm text-platforma-muted">{label("noEffects")}</p><div className="flex gap-2"><Button variant="secondary" disabled={busy || dirty} onClick={async () => { const next = await run(() => importWorkspaceApi.preview(data.id, data.version)); if (next?.report.rows) setStep("preview"); }}>{label("check")}</Button><Button disabled={busy || dirty || data.state !== "ready" || data.validated_version !== data.version || !data.report.ready} onClick={() => setDialog("confirm")}>{label("confirm")}</Button></div></div>}
          </>}
        </>}
      </div>
    </div>
    <Modal open={!!dialog} title={label(dialog === "confirm" ? "confirm" : "cancel")} onClose={() => { if (!busy) setDialog(null); }}><div className="space-y-4"><p className="text-sm">{label(dialog === "confirm" ? "confirmHint" : "cancelHint")}</p>{dialog === "confirm" && <p className="text-sm text-platforma-muted">{label("noEffects")}</p>}<div className="flex justify-end gap-2"><Button variant="secondary" disabled={busy} onClick={() => setDialog(null)}>{label("close")}</Button><Button disabled={busy} onClick={async () => { if (!data) return; const next = await run(() => dialog === "confirm" ? importWorkspaceApi.confirm(data.id, data.version) : importWorkspaceApi.cancel(data.id, data.version)); if (next) { setDialog(null); if (next.state === "imported") setStep("preview"); } }}>{label(dialog === "confirm" ? "confirm" : "cancel")}</Button></div></div></Modal>
    <Modal open={blocker.state === "blocked"} title={label("dirty")} onClose={() => blocker.state === "blocked" && blocker.reset()}><div className="flex justify-end gap-2"><Button variant="secondary" onClick={() => blocker.state === "blocked" && blocker.reset()}>{label("close")}</Button><Button disabled={busy} onClick={() => blocker.state === "blocked" && blocker.proceed()}>{label("discard")}</Button></div></Modal>
  </main>;
}

function SourceEditor({ source, workspace, step, focusRow, busy, onDirty, onSave, onDuplicate, onRemove }: {
  source: ImportSource; workspace: ImportWorkspace; step: "fields" | "data"; focusRow?: number; busy: boolean;
  onDirty: (dirty: boolean) => void; onSave: (source: ImportSource) => Promise<ImportWorkspace | undefined>;
  onDuplicate: (kind: ImportEntity) => Promise<ImportWorkspace | undefined>;
  onRemove: () => Promise<ImportWorkspace | undefined>;
}) {
  const { t } = useI18n(); const label = (key: string) => t(`importWorkspace.${key}`);
  const [removeOpen, setRemoveOpen] = useState(false);
  const [draft, setDraft] = useState(source); const [copyType, setCopyType] = useState<ImportEntity>("appointments");
  const dirty = JSON.stringify(draft) !== JSON.stringify(source);
  useEffect(() => { onDirty(dirty); return () => onDirty(false); }, [dirty, onDirty]);
  return <Card padding="md" className="space-y-4">
    {step === "fields" ? <><SourceMapping businessId={workspace.business} source={draft} fields={workspace.mapping_fields} onChange={setDraft} disabled={busy} /><div className="flex flex-wrap items-end gap-2 border-t border-platforma-border pt-3"><Select label={label("copy")} value={copyType} disabled={busy || dirty} options={importEntities.filter(kind => kind !== source.entity_type).map(value => ({ value, label: label(value) }))} onChange={event => setCopyType(event.target.value as ImportEntity)} /><Button variant="secondary" disabled={busy || dirty || copyType === source.entity_type} onClick={() => void onDuplicate(copyType)}>{label("copy")}</Button><Button variant="ghost" disabled={busy || dirty} onClick={() => setRemoveOpen(true)}>{label("removeSource")}</Button></div></> : <SourceRows workspaceId={workspace.id} version={workspace.version} source={draft} onChange={setDraft} disabled={busy} initialRow={focusRow} />}
    <Modal open={removeOpen} title={label("removeSource")} onClose={() => { if (!busy) setRemoveOpen(false); }}><div className="space-y-4"><p className="text-sm">{label("removeSourceHint")}</p><div className="flex justify-end gap-2"><Button variant="secondary" disabled={busy} onClick={() => setRemoveOpen(false)}>{label("close")}</Button><Button disabled={busy} onClick={async () => { if (await onRemove()) setRemoveOpen(false); }}>{label("removeSource")}</Button></div></div></Modal>
    <div className="flex flex-wrap items-center justify-end gap-2 border-t border-platforma-border pt-3">{dirty && <p className="mr-auto text-sm text-platforma-muted">{label("dirty")}</p>}<Button variant="ghost" disabled={!dirty || busy} onClick={() => setDraft(source)}>{label("discard")}</Button><Button disabled={!dirty || busy} onClick={() => void onSave(draft)}>{label("save")}</Button></div>
  </Card>;
}

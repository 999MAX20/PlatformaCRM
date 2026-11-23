import { useCallback, useEffect, useRef, useState } from "react";
import { medicalDocumentRulesApi as api, type DocumentRuleAccess, type DocumentRuleVersion } from "../../../api/medicalDocumentRules";
import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import type { RoleFormControl } from "../roles/MedicalRoleCommand";
import { medicalRoleDenied } from "../roles/useMedicalRolePage";
import { DocumentRuleEditor } from "./DocumentRuleEditor";
import { DocumentRequirementsSummary as RequirementsSummary } from "./DocumentRequirementsSummary";

export function DocumentRuleWorkspace({ businessId, control }: { businessId: number; control: RoleFormControl }) {
  const { t } = useI18n();
  const [access, setAccess] = useState<DocumentRuleAccess | null>(null);
  const [rows, setRows] = useState<DocumentRuleVersion[]>([]);
  const [next, setNext] = useState<number | null>(null);
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<DocumentRuleVersion | "create" | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const request = useRef<AbortController | null>(null);
  const returnTo = useRef<string | null>(null);
  const load = useCallback(async (before?: number) => {
    request.current?.abort(); const controller = new AbortController(); request.current = controller;
    setLoading(true); setError(null); if (!before) { setRows([]); setNext(null); }
    try {
      const [permissions, page] = await Promise.all([api.access(businessId, controller.signal), api.list(businessId, search, before, controller.signal)]);
      if (!controller.signal.aborted) { setAccess(permissions); setRows(previous => before ? [...previous, ...page.results] : page.results); setNext(page.next_before_id); }
    } catch (cause) { if (!controller.signal.aborted) { if (medicalRoleDenied(cause)) { setAccess(null); setRows([]); setSelected(null); control.onDenied(cause); } else setError(cause); } }
    finally { if (!controller.signal.aborted) setLoading(false); }
  }, [businessId, search, control.onDenied]);
  useEffect(() => { void load(); return () => request.current?.abort(); }, [load]);
  useEffect(() => { if (!loading && !selected && returnTo.current) { document.getElementById(returnTo.current)?.focus(); returnTo.current = null; } }, [loading, selected, rows]);
  function close(saved = false) {
    if (control.guard.current.pending || (!saved && control.guard.current.dirty && !window.confirm(t("medical.clinical.discard")))) return;
    control.guard.current = { dirty: false, pending: false }; control.onDraft(control.guard.current);
    setSelected(null); void load();
  }
  function open(row: DocumentRuleVersion | "create") { returnTo.current = row === "create" ? "document-rule-create" : `document-rule-${row.kind_id}`; setSelected(row); }
  const editorControl = { ...control, onSaved: () => close(true) };
  return <section className="min-w-0 space-y-4" data-testid="document-rules">
    <p role="status" className="text-sm text-platforma-subtle">{t("medical.rules.synthetic")}</p>
    {selected && access ? <>
      <Button size="lg" variant="secondary" onClick={() => close()}>{t("common.back")}</Button>
      {selected === "create" ? <DocumentRuleEditor businessId={businessId} version={null} access={access} control={editorControl} /> :
        <DocumentRuleDetail key={selected.kind_id} businessId={businessId} version={selected} access={access} control={editorControl} />}
    </> : <>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end"><div className="min-w-0 flex-1"><Input label={t("medical.rules.search")}
        value={query} maxLength={255} onChange={event => setQuery(event.target.value)} onKeyDown={event => { if (event.key === "Enter") { event.preventDefault(); if (search === query) void load(); else setSearch(query); } }} /></div>
        <Button size="lg" variant="secondary" disabled={loading} onClick={() => { if (search === query) void load(); else setSearch(query); }}>{t("common.search")}</Button>
        {access?.actions.save ? <Button id="document-rule-create" size="lg" disabled={loading} onClick={() => open("create")}>{t("medical.rules.create")}</Button> : null}
      </div>
      {error ? <ErrorState message={getApiErrorMessage(error)} action={<Button size="lg" onClick={() => void load()}>{t("common.retry")}</Button>} /> : null}
      <ul className="divide-y divide-platforma-border">{rows.map(row => <li key={row.kind_id} className="flex flex-wrap items-center justify-between gap-3 py-3">
        <div className="min-w-0 break-words"><p className="font-medium">{row.content.name}</p><p className="text-sm">{t("medical.templates.version", { revision: row.revision })}</p></div>
        <Button id={`document-rule-${row.kind_id}`} size="lg" variant="secondary" disabled={loading} onClick={() => open(row)}>{t("medical.templates.open")}</Button>
      </li>)}</ul>
      {loading ? <LoadingState /> : !error && !rows.length ? <p>{t("medical.rules.empty")}</p> : null}
      {next && !error ? <Button size="lg" variant="secondary" disabled={loading} onClick={() => void load(next)}>{t("medical.templates.more")}</Button> : null}
    </>}
  </section>;
}

function DocumentRuleDetail({ businessId, version: initial, access, control }: {
  businessId: number; version: DocumentRuleVersion; access: DocumentRuleAccess; control: RoleFormControl;
}) {
  const { t } = useI18n();
  const [version, setVersion] = useState(initial);
  const [current, setCurrent] = useState(initial.revision);
  const [editing, setEditing] = useState(false);
  const [history, setHistory] = useState<DocumentRuleVersion[]>([]);
  const [before, setBefore] = useState<number | undefined>();
  const [next, setNext] = useState<number | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError(null);
    api.history(businessId, initial.kind_id, before, controller.signal).then(page => {
      if (!controller.signal.aborted) { setHistory(previous => before ? [...previous, ...page.results] : page.results); setCurrent(page.current_revision); setNext(page.next_before_id); }
    }).catch(cause => { if (!controller.signal.aborted) { if (medicalRoleDenied(cause)) control.onDenied(cause); else setError(cause); } })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [businessId, initial.kind_id, before, attempt, control.onDenied]);
  if (editing) return <DocumentRuleEditor businessId={businessId} version={version} access={access} control={control} />;
  return <div className="space-y-4" data-testid="document-rule-detail">
    <h2 className="break-words text-lg font-semibold">{version.content.name}</h2>
    <p>{t("medical.templates.version", { revision: version.revision })}</p>
    <p>{t(version.content.docx_allowed ? "medical.rules.docxEnabled" : "medical.rules.docxDisabled")}</p>
    <section className="space-y-2"><h3 className="font-semibold">{t("medical.rules.templates")}</h3>
      <ul>{version.content.templates.map(item => <li key={item.id} className="break-words text-sm">{item.title}</li>)}</ul></section>
    <section className="space-y-2"><h3 className="font-semibold">{t("medical.rules.default")}</h3><RequirementsSummary value={version.content.default} /></section>
    {version.content.services.map(item => <section key={item.id} className="space-y-2 border-t border-platforma-border pt-3">
      <h3 className="break-words font-semibold">{item.name}</h3><RequirementsSummary value={item.rule} /></section>)}
    <p className="whitespace-pre-wrap break-words text-sm">{t("medical.templates.reason")}: {version.reason}</p>
    {access.actions.save && version.revision === current && !loading && !error ? <Button size="lg" onClick={() => setEditing(true)}>{t("medical.templates.newVersion")}</Button> : null}
    <h3 className="font-semibold">{t("medical.rules.history")}</h3>
    {error ? <ErrorState message={getApiErrorMessage(error)} action={<Button size="lg" onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button>} /> : null}
    <div className="flex flex-wrap gap-2">{history.map(item => <Button key={item.version_id} size="lg" variant="secondary" aria-pressed={version.version_id === item.version_id}
      onClick={() => setVersion(item)}>{t("medical.templates.version", { revision: item.revision })}</Button>)}</div>
    {loading ? <LoadingState /> : null}
    {next && !error ? <Button size="lg" variant="secondary" disabled={loading} onClick={() => setBefore(next)}>{t("medical.templates.more")}</Button> : null}
  </div>;
}

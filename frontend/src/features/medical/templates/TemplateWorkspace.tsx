import { useCallback, useEffect, useRef, useState } from "react";
import { medicalTemplatesApi as api, commonTemplatesApi, type TemplateAccess, type TemplateRow, type TemplateVersion, type TemplateVersionRow, type TemplateSearch as SearchFilters } from "../../../api/medicalTemplates";
import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { Modal } from "../../../components/ui/Modal";
import { Select } from "../../../components/ui/Select";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import type { RoleDraftState } from "../roles/MedicalRoleCommand";
import { medicalRoleDenied } from "../roles/useMedicalRolePage";
import { TemplateEditor } from "./TemplateEditor";
import { TemplateClassificationSummary } from "./TemplateClassification";
import { TemplateSearch } from "./TemplateSearch";
import { TemplateAvailabilityDetail } from "./TemplateAvailability";
import { TemplateReviewDetail, TemplateReviewStatus, TemplateSubmit } from "./TemplateReview";
import { DocumentRuleWorkspace } from "./DocumentRuleWorkspace";
import { TemplateDocx } from "./TemplateDocx";

export function TemplateWorkspace({ businessId, active, onDraft }: {
  businessId: number; active: boolean; onDraft: (state: RoleDraftState) => void;
}) {
  const { t } = useI18n();
  const [access, setAccess] = useState<TemplateAccess | null>(null);
  const [commonAccess, setCommonAccess] = useState<TemplateAccess | null>(null);
  const [rows, setRows] = useState<TemplateRow[]>([]);
  const [cursor, setCursor] = useState<number | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [mode, setMode] = useState<"personal" | "common" | "reviews" | "availability" | "rules">("personal");
  const [activity, setActivity] = useState<"all" | "active" | "inactive">("all");
  const [filters, setFilters] = useState<SearchFilters>({});
  const appliedFilters = useRef<SearchFilters>({});
  const [dialog, setDialog] = useState<"create" | TemplateRow | null>(null);
  const guard = useRef<RoleDraftState>({ dirty: false, pending: false });
  const request = useRef<AbortController | null>(null);
  const focusReturn = useRef("medical-template-create");
  const denied = useCallback((cause: unknown) => {
    setRows([]); setAccess(null); setCommonAccess(null); setDialog(null); setCursor(null); setError(cause);
    appliedFilters.current = {}; setFilters({});
    guard.current = { dirty: false, pending: false }; onDraft(guard.current);
  }, [onDraft]);
  const load = useCallback(async (before?: number) => {
    request.current?.abort();
    const controller = new AbortController(); request.current = controller;
    const searchFilters = appliedFilters.current;
    setLoading(true); setError(null);
    try {
      const permissions = await api.access(businessId, controller.signal);
      if ((mode === "reviews" || mode === "availability" || mode === "rules") && (!permissions.actions.approve || permissions.kind !== "head")) { setMode("personal"); setRows([]); setCursor(null); setAccess(permissions); return; }
      let shared: TemplateAccess | null = null;
      if (permissions.kind === "head") {
        try { shared = await commonTemplatesApi.access(businessId, controller.signal); }
        catch (cause) { if (!medicalRoleDenied(cause)) throw cause; }
      }
      if (controller.signal.aborted) return;
      setCommonAccess(shared);
      if (mode === "rules") { setAccess(permissions); setRows([]); setCursor(null); return; }
      if (mode === "common" && !shared) { setMode("personal"); setRows([]); setCursor(null); setAccess(permissions); return; }
      const page = mode === "availability" ? await api.managed(businessId, before, controller.signal, { ...searchFilters, activity }) : mode === "common" ? await commonTemplatesApi.list(businessId, before, controller.signal, searchFilters) : mode === "reviews" ? await api.pending(businessId, before, controller.signal) : await api.list(businessId, before, controller.signal, searchFilters);
      if (controller.signal.aborted) return;
      const items = page.results.map(row => ({ ...row, created_at: "created_at" in row ? row.created_at : row.submitted_at }));
      setAccess(permissions); setRows(previous => before ? [...previous, ...items] : items); setCursor(page.next_before_id);
    } catch (cause) {
      if (!controller.signal.aborted) { if (medicalRoleDenied(cause)) denied(cause); else setError(cause); }
    } finally { if (!controller.signal.aborted) setLoading(false); }
  }, [businessId, denied, mode, activity]);
  useEffect(() => {
    if (active && !guard.current.dirty && !guard.current.pending) void load();
    return () => request.current?.abort();
  }, [active, attempt, load]);
  function close() {
    if (guard.current.pending || (guard.current.dirty && !window.confirm(t("medical.clinical.discard")))) return;
    guard.current = { dirty: false, pending: false }; onDraft(guard.current); setDialog(null);
  }
  function saved() {
    guard.current = { dirty: false, pending: false }; onDraft(guard.current);
    setDialog(null); setLoading(true); setAttempt(value => value + 1);
  }
  function open(value: "create" | TemplateRow) {
    focusReturn.current = value === "create" ? "medical-template-create" : `medical-template-${value.template_id}`;
    setDialog(value);
  }
  const draftApi = mode === "common" ? commonTemplatesApi : api;
  const draftAccess = mode === "common" ? commonAccess : access;
  const createLabel = mode === "common" ? "medical.templates.commonCreate" : "medical.templates.create";
  if (!active && !access) return null;
  return <div className="space-y-4" data-testid="medical-template-workspace">
    {mode !== "rules" ? <p className="text-sm text-platforma-subtle" role="status">{t("medical.templates.draftStatus")}</p> : null}
    {access?.actions.approve || commonAccess ? <div className="flex flex-wrap gap-2">
      {(["personal", ...(commonAccess ? ["common" as const] : []), ...(access?.actions.approve && access.kind === "head" ? ["reviews" as const, "availability" as const, "rules" as const] : [])] as const).map(value => <Button key={value} variant={mode === value ? "primary" : "secondary"} aria-pressed={mode === value}
        onClick={() => { if (mode === value || guard.current.pending || (guard.current.dirty && !window.confirm(t("medical.clinical.discard")))) return;
          guard.current = { dirty: false, pending: false }; onDraft(guard.current); setRows([]); setCursor(null); setLoading(true); setMode(value); }} disabled={loading}>
        {t(value === "rules" ? "medical.rules.title" : value === "personal" ? "medical.templates.personal" : value === "common" ? "medical.templates.common" : value === "availability" ? "medical.templates.availability" : "medical.templates.queue")}</Button>)}
    </div> : null}
    {mode === "rules" ? access ? <DocumentRuleWorkspace businessId={businessId} control={{ guard, onDraft, onSaved: saved, onDenied: denied }} /> :
      error ? <ErrorState message={getApiErrorMessage(error)} /> : <LoadingState /> : <>
    {mode !== "reviews" && access ? <TemplateSearch value={filters} disabled={loading}
      onApply={value => { appliedFilters.current = value; setLoading(true); setRows([]); setCursor(null); setFilters(value); setAttempt(previous => previous + 1); }} /> : null}
    {mode === "availability" ? <Select label={t("medical.templates.availability")} value={activity} disabled={loading}
      options={(["all", "active", "inactive"] as const).map(value => ({ value, label: t(value === "all" ? "medical.templates.allStatuses" : `medical.templates.${value}`) }))}
      onChange={event => { if (event.target.value === activity) return; setLoading(true); setRows([]); setCursor(null); setActivity(event.target.value as typeof activity); }} /> : null}
    <div className="flex flex-wrap gap-2">
      {(mode === "personal" || mode === "common") && draftAccess?.actions.create ? <Button id="medical-template-create" onClick={() => open("create")}>{t(createLabel)}</Button> : null}
      <Button variant="secondary" disabled={loading} onClick={() => setAttempt(value => value + 1)}>{t("medical.clinical.reload")}</Button>
    </div>
    {error ? <ErrorState message={getApiErrorMessage(error)} action={<Button variant="secondary" onClick={() => void load()}>{t("common.retry")}</Button>} /> : null}
    <ul className="divide-y divide-platforma-border">{rows.map(row => <li key={row.template_id} className="flex flex-wrap items-center justify-between gap-3 py-3">
      <div className="min-w-0 w-full break-words sm:w-auto sm:flex-1"><p className="font-medium">{row.title}</p><p className="text-sm text-platforma-subtle">{t("medical.templates.version", { revision: row.revision })}</p></div>
      {mode === "availability" && row.availability ? <p className="text-sm">{t(row.availability.is_active ? "medical.templates.active" : "medical.templates.inactive")}</p> : null}
      <Button id={`medical-template-${row.template_id}`} variant="secondary" disabled={loading} onClick={() => open(row)}>{t("medical.templates.open")}</Button>
    </li>)}</ul>
    {loading ? <LoadingState /> : !error && !rows.length ? <p className="text-sm text-platforma-subtle">{t(mode === "reviews" ? "medical.templates.queueEmpty" : Object.values(filters).some(Boolean) || (mode === "availability" && activity !== "all") ? "medical.templates.noMatches" : mode === "availability" ? "medical.templates.managedEmpty" : mode === "common" ? "medical.templates.commonEmpty" : "medical.templates.empty")}</p> : null}
    {cursor && !error ? <Button variant="secondary" disabled={loading} onClick={() => void load(cursor)}>{t("medical.templates.more")}</Button> : null}
    <Modal open={dialog !== null} onClose={close} closeOnBackdrop={false} size="lg" focusReturnId={focusReturn.current}
      title={t(dialog === "create" ? createLabel : "medical.templates.open")}>
      {dialog === "create" ? <TemplateEditor api={draftApi} businessId={businessId} version={null} control={{ guard, onDraft, onSaved: saved, onDenied: denied }} /> : dialog && access ?
        mode === "availability" ? <TemplateAvailabilityDetail businessId={businessId} row={dialog} control={{ guard, onDraft, onSaved: saved, onDenied: denied }} /> :
        mode === "reviews" ? <TemplateReviewDetail businessId={businessId} versionId={dialog.version_id} control={{ guard, onDraft, onSaved: saved, onDenied: denied }} /> :
        <TemplateDetail api={draftApi} businessId={businessId} row={dialog} canUpdate={!!draftAccess?.actions.update}
          control={{ guard, onDraft, onSaved: saved, onDenied: denied }} /> : null}
    </Modal>
    </>}
  </div>;
}

function TemplateDetail({ businessId, row, canUpdate, control, api }: {
  api: typeof commonTemplatesApi;
  businessId: number; row: TemplateRow; canUpdate: boolean;
  control: Parameters<typeof TemplateEditor>[0]["control"];
}) {
  const { t } = useI18n();
  const [versionId, setVersionId] = useState(row.version_id);
  const [version, setVersion] = useState<TemplateVersion | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  const [editing, setEditing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  useEffect(() => {
    const controller = new AbortController(); setVersion(null); setError(null);
    void api.version(businessId, versionId, controller.signal).then(value => { if (!controller.signal.aborted) setVersion(value); })
      .catch(cause => { if (!controller.signal.aborted) { if (medicalRoleDenied(cause)) control.onDenied(cause); else setError(cause); } });
    return () => controller.abort();
  }, [api, businessId, versionId, attempt, control.onDenied]);
  if (error) return <ErrorState message={getApiErrorMessage(error)} action={<Button onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button>} />;
  if (!version) return <LoadingState />;
  if (editing) return <TemplateEditor api={api} version={version} businessId={businessId} control={control} />;
  return <div className="space-y-4">
    <h2 className="break-words text-base font-semibold">{version.template.title}</h2>
    <p className="text-sm text-platforma-subtle">{t("medical.templates.version", { revision: version.revision })}</p>
    <div className="whitespace-pre-wrap break-words text-sm">{version.template.text}</div>
    <TemplateReviewStatus review={version.review} />
    <TemplateClassificationSummary value={version.metadata} />
    <TemplateDocx key={version.version_id} businessId={businessId} versionId={version.version_id} onDenied={control.onDenied} />
    {version.reason ? <p className="whitespace-pre-wrap break-words text-sm">{t("medical.templates.reason")}: {version.reason}</p> : null}
    {!submitting && canUpdate && version.revision === version.current_revision ? <Button onClick={() => setEditing(true)}>{t(version.review ? "medical.templates.newVersion" : "medical.templates.edit")}</Button> : null}
    {canUpdate && version.revision === version.current_revision && !version.review ?
      submitting ? <TemplateSubmit submit={api.submit} key={version.version_id} businessId={businessId} versionId={version.version_id} control={control} /> :
        <Button onClick={() => setSubmitting(true)}>{t("medical.templates.submit")}</Button> : null}
    {!submitting ? <TemplateHistory api={api} businessId={businessId} templateId={row.template_id} onSelect={setVersionId} onDenied={control.onDenied} /> : null}
  </div>;
}

function TemplateHistory({ businessId, templateId, onSelect, onDenied, api }: {
  api: typeof commonTemplatesApi;
  businessId: number; templateId: number; onSelect: (id: number) => void; onDenied: (cause: unknown) => void;
}) {
  const { t } = useI18n();
  const [rows, setRows] = useState<TemplateVersionRow[]>([]);
  const [cursor, setCursor] = useState<number | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const request = useRef<AbortController | null>(null);
  const load = useCallback(async (before?: number) => {
    request.current?.abort(); const controller = new AbortController(); request.current = controller;
    setLoading(true); setError(null);
    try {
      const page = await api.history(businessId, templateId, before, controller.signal);
      if (!controller.signal.aborted) { setRows(previous => before ? [...previous, ...page.results] : page.results); setCursor(page.next_before_revision); }
    } catch (cause) { if (!controller.signal.aborted) { if (medicalRoleDenied(cause)) onDenied(cause); else setError(cause); } }
    finally { if (!controller.signal.aborted) setLoading(false); }
  }, [api, businessId, templateId, onDenied]);
  useEffect(() => { void load(); return () => request.current?.abort(); }, [load]);
  return <section className="space-y-2" aria-label={t("medical.templates.history")}>
    <h3 className="text-base font-semibold">{t("medical.templates.history")}</h3>
    <div className="flex flex-wrap gap-2">{rows.map(row => <Button key={row.version_id} variant="secondary" onClick={() => onSelect(row.version_id)}>{t("medical.templates.version", { revision: row.revision })}</Button>)}</div>
    {loading ? <LoadingState /> : null}
    {error ? <ErrorState message={getApiErrorMessage(error)} action={<Button onClick={() => void load()}>{t("common.retry")}</Button>} /> : null}
    {cursor && !error ? <Button variant="secondary" disabled={loading} onClick={() => void load(cursor)}>{t("medical.templates.more")}</Button> : null}
  </section>;
}

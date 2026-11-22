import { useCallback, useEffect, useRef, useState } from "react";
import { medicalTemplatesApi as api, type TemplateAccess, type TemplateRow, type TemplateVersion, type TemplateVersionRow } from "../../../api/medicalTemplates";
import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { Modal } from "../../../components/ui/Modal";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import type { RoleDraftState } from "../roles/MedicalRoleCommand";
import { medicalRoleDenied } from "../roles/useMedicalRolePage";
import { TemplateEditor } from "./TemplateEditor";

export function TemplateWorkspace({ businessId, active, onDraft }: {
  businessId: number; active: boolean; onDraft: (state: RoleDraftState) => void;
}) {
  const { t } = useI18n();
  const [access, setAccess] = useState<TemplateAccess | null>(null);
  const [rows, setRows] = useState<TemplateRow[]>([]);
  const [cursor, setCursor] = useState<number | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [dialog, setDialog] = useState<"create" | TemplateRow | null>(null);
  const guard = useRef<RoleDraftState>({ dirty: false, pending: false });
  const request = useRef<AbortController | null>(null);
  const focusReturn = useRef("medical-template-create");
  const denied = useCallback((cause: unknown) => {
    setRows([]); setAccess(null); setDialog(null); setCursor(null); setError(cause);
    guard.current = { dirty: false, pending: false }; onDraft(guard.current);
  }, [onDraft]);
  const load = useCallback(async (before?: number) => {
    request.current?.abort();
    const controller = new AbortController(); request.current = controller;
    setLoading(true); setError(null);
    try {
      const permissions = await api.access(businessId, controller.signal);
      const page = await api.list(businessId, before, controller.signal);
      if (controller.signal.aborted) return;
      setAccess(permissions); setRows(previous => before ? [...previous, ...page.results] : page.results); setCursor(page.next_before_id);
    } catch (cause) {
      if (!controller.signal.aborted) { if (medicalRoleDenied(cause)) denied(cause); else setError(cause); }
    } finally { if (!controller.signal.aborted) setLoading(false); }
  }, [businessId, denied]);
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
  if (!active && !access) return null;
  return <div className="space-y-4" data-testid="medical-template-workspace">
    <p className="text-sm text-platforma-subtle" role="status">{t("medical.templates.draftStatus")}</p>
    <div className="flex flex-wrap gap-2">
      {access?.actions.create ? <Button id="medical-template-create" onClick={() => open("create")}>{t("medical.templates.create")}</Button> : null}
      <Button variant="secondary" disabled={loading} onClick={() => setAttempt(value => value + 1)}>{t("medical.clinical.reload")}</Button>
    </div>
    {error ? <ErrorState message={getApiErrorMessage(error)} action={<Button variant="secondary" onClick={() => void load()}>{t("common.retry")}</Button>} /> : null}
    <ul className="divide-y divide-platforma-border">{rows.map(row => <li key={row.template_id} className="flex flex-wrap items-center justify-between gap-3 py-3">
      <div className="min-w-0 flex-1 break-words"><p className="font-medium">{row.title}</p><p className="text-sm text-platforma-subtle">{t("medical.templates.version", { revision: row.revision })}</p></div>
      <Button id={`medical-template-${row.template_id}`} variant="secondary" disabled={loading} onClick={() => open(row)}>{t("medical.templates.open")}</Button>
    </li>)}</ul>
    {loading ? <LoadingState /> : !error && !rows.length ? <p className="text-sm text-platforma-subtle">{t("medical.templates.empty")}</p> : null}
    {cursor && !error ? <Button variant="secondary" disabled={loading} onClick={() => void load(cursor)}>{t("medical.templates.more")}</Button> : null}
    <Modal open={dialog !== null} onClose={close} closeOnBackdrop={false} size="lg" focusReturnId={focusReturn.current}
      title={t(dialog === "create" ? "medical.templates.create" : "medical.templates.open")}>
      {dialog === "create" ? <TemplateEditor businessId={businessId} version={null} control={{ guard, onDraft, onSaved: saved, onDenied: denied }} /> : dialog && access ?
        <TemplateDetail businessId={businessId} row={dialog} canUpdate={access.actions.update}
          control={{ guard, onDraft, onSaved: saved, onDenied: denied }} /> : null}
    </Modal>
  </div>;
}

function TemplateDetail({ businessId, row, canUpdate, control }: {
  businessId: number; row: TemplateRow; canUpdate: boolean;
  control: Parameters<typeof TemplateEditor>[0]["control"];
}) {
  const { t } = useI18n();
  const [versionId, setVersionId] = useState(row.version_id);
  const [version, setVersion] = useState<TemplateVersion | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  const [editing, setEditing] = useState(false);
  useEffect(() => {
    const controller = new AbortController(); setVersion(null); setError(null);
    void api.version(businessId, versionId, controller.signal).then(value => { if (!controller.signal.aborted) setVersion(value); })
      .catch(cause => { if (!controller.signal.aborted) { if (medicalRoleDenied(cause)) control.onDenied(cause); else setError(cause); } });
    return () => controller.abort();
  }, [businessId, versionId, attempt, control.onDenied]);
  if (error) return <ErrorState message={getApiErrorMessage(error)} action={<Button onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button>} />;
  if (!version) return <LoadingState />;
  if (editing) return <TemplateEditor version={version} businessId={businessId} control={control} />;
  return <div className="space-y-4">
    <h2 className="break-words text-base font-semibold">{version.template.title}</h2>
    <p className="text-sm text-platforma-subtle">{t("medical.templates.version", { revision: version.revision })}</p>
    <div className="whitespace-pre-wrap break-words text-sm">{version.template.text}</div>
    {version.reason ? <p className="whitespace-pre-wrap break-words text-sm">{t("medical.templates.reason")}: {version.reason}</p> : null}
    {canUpdate && version.revision === version.current_revision ? <Button onClick={() => setEditing(true)}>{t("medical.templates.edit")}</Button> : null}
    <TemplateHistory businessId={businessId} templateId={row.template_id} onSelect={setVersionId} onDenied={control.onDenied} />
  </div>;
}

function TemplateHistory({ businessId, templateId, onSelect, onDenied }: {
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
  }, [businessId, templateId, onDenied]);
  useEffect(() => { void load(); return () => request.current?.abort(); }, [load]);
  return <section className="space-y-2" aria-label={t("medical.templates.history")}>
    <h3 className="text-base font-semibold">{t("medical.templates.history")}</h3>
    <div className="flex flex-wrap gap-2">{rows.map(row => <Button key={row.version_id} variant="secondary" onClick={() => onSelect(row.version_id)}>{t("medical.templates.version", { revision: row.revision })}</Button>)}</div>
    {loading ? <LoadingState /> : null}
    {error ? <ErrorState message={getApiErrorMessage(error)} action={<Button onClick={() => void load()}>{t("common.retry")}</Button>} /> : null}
    {cursor && !error ? <Button variant="secondary" disabled={loading} onClick={() => void load(cursor)}>{t("medical.templates.more")}</Button> : null}
  </section>;
}

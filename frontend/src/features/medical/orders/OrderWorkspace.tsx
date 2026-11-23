import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { medicalOrdersApi as api, medicationFields, type OrderAccess, type OrderScope, type OrderVersion } from "../../../api/medicalOrders";
import type { AppointmentClinicalContext } from "../../../api/medicalClinical";
import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { Modal } from "../../../components/ui/Modal";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import { formatDateTime } from "../../../lib/format";
import { localeByLanguage } from "../../calendar/calendarConstants";
import { useUnsavedEntryWarning } from "../../auth/useUnsavedEntryWarning";
import { medicalRoleDenied } from "../roles/useMedicalRolePage";
import type { RoleDraftState } from "../roles/MedicalRoleCommand";
import { OrderEditor } from "./OrderEditor";

export function OrderWorkspace({ context, active, onEditor, canEdit }: {
  context: AppointmentClinicalContext; active: boolean; onEditor: (open: boolean) => void; canEdit: () => boolean;
}) {
  const { t, language } = useI18n();
  const scope = useMemo<OrderScope>(() => ({ business_id: context.business_id, patient_id: context.patient.id,
    appointment_id: context.appointment.id, encounter_id: context.encounter!.id }), [context]);
  const [rows, setRows] = useState<OrderVersion[]>([]);
  const [access, setAccess] = useState<OrderAccess | null>(null);
  const [cursor, setCursor] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [editor, setEditor] = useState<"create" | OrderVersion | null>(null);
  const [history, setHistory] = useState<number | null>(null);
  const [draft, setDraft] = useState<RoleDraftState>({ dirty: false, pending: false });
  const guard = useRef<RoleDraftState>({ dirty: false, pending: false });
  const request = useRef<AbortController | null>(null);
  const focusId = useRef("medical-order-create");
  const historyFocusId = useRef("");
  useUnsavedEntryWarning(draft.dirty || draft.pending);
  const denied = useCallback((cause: unknown) => {
    setRows([]); setAccess(null); setEditor(null); setHistory(null); setError(cause);
    guard.current = { dirty: false, pending: false }; setDraft(guard.current); onEditor(false);
  }, [onEditor]);
  const load = useCallback(async (before?: number) => {
    request.current?.abort(); const controller = new AbortController(); request.current = controller;
    setLoading(true); setError(null);
    try {
      const permissions = await api.access(scope, controller.signal);
      const page = await api.list(scope, before, controller.signal);
      if (!controller.signal.aborted) {
        setAccess(permissions); setRows(previous => before ? [...previous, ...page.results] : page.results); setCursor(page.next_before_id);
      }
    } catch (cause) { if (!controller.signal.aborted) { if (medicalRoleDenied(cause)) denied(cause); else setError(cause); } }
    finally { if (!controller.signal.aborted) setLoading(false); }
  }, [scope, denied]);
  useEffect(() => { if (active) void load(); return () => request.current?.abort(); }, [active, load]);
  useEffect(() => () => onEditor(false), [onEditor]);
  function openEditor(value: "create" | OrderVersion) {
    if (!canEdit()) return;
    focusId.current = value === "create" ? "medical-order-create" : `medical-order-edit-${value.order_id}`;
    setEditor(value); onEditor(true);
  }
  function closeEditor() {
    if (guard.current.pending || (guard.current.dirty && !window.confirm(t("medical.clinical.discard")))) return;
    setEditor(null); onEditor(false);
  }
  function saved() { setEditor(null); onEditor(false); void load(); }
  return <section className="min-w-0 space-y-4" data-testid="medical-orders">
    <div className="flex flex-wrap gap-2">
      {access?.actions.create ? <Button size="lg" data-focus-return-id="medical-order-create" disabled={loading} onClick={() => openEditor("create")}>{t("medical.orders.create")}</Button> : null}
      <Button size="lg" variant="secondary" disabled={loading} onClick={() => void load()}>{t("medical.clinical.reload")}</Button>
    </div>
    {loading ? <LoadingState /> : null}
    {error ? <ErrorState message={medicalRoleDenied(error) ? t("medical.denied") : getApiErrorMessage(error)}
      action={<Button size="lg" onClick={() => void load()}>{t("common.retry")}</Button>} /> : null}
    {!loading && !error && !rows.length ? <p className="text-sm text-platforma-subtle">{t("medical.orders.empty")}</p> : null}
    <ul className="divide-y divide-platforma-border">{rows.map(row => <li key={row.order_id} className="min-w-0 space-y-3 py-4">
      <h3 className="text-base font-semibold">{t(`medical.orders.${row.content.kind}`)}</h3>
      <p className="break-words text-sm text-platforma-subtle">{t("medical.orders.draft")} · {row.author_name} · {formatDateTime(row.created_at, undefined, true, localeByLanguage[language])}</p>
      <OrderContentView version={row} />
      <div className="flex flex-wrap gap-2">
        {access?.actions.update && access.actor_id === row.author_id ? <Button size="lg" variant="secondary"
          data-focus-return-id={`medical-order-edit-${row.order_id}`} disabled={loading} onClick={() => openEditor(row)}>{t("common.edit")}</Button> : null}
        <Button size="lg" variant="secondary" disabled={loading} data-focus-return-id={`medical-order-history-${row.order_id}`} onClick={() => {
          historyFocusId.current = `medical-order-history-${row.order_id}`; setHistory(row.order_id); onEditor(true);
        }}>{t("medical.orders.history")}</Button>
      </div>
    </li>)}</ul>
    {cursor !== null ? <Button size="lg" variant="secondary" disabled={loading} onClick={() => void load(cursor)}>{t("medical.clinical.older")}</Button> : null}
    <Modal open={editor !== null} onClose={closeEditor} title={t(editor === "create" ? "medical.orders.create" : "common.edit")}
      size="lg" closeOnBackdrop={false} focusReturnId={focusId.current} testId="medical-order-editor">
      {editor !== null ? <OrderEditor key={typeof editor === "string" ? editor : editor.version_id} scope={scope}
        version={editor === "create" ? null : editor} control={{ guard, onDraft: setDraft, onSaved: saved, onDenied: denied }} /> : null}
    </Modal>
    <Modal open={history !== null} onClose={() => { setHistory(null); onEditor(false); }} title={t("medical.orders.history")}
      size="lg" focusReturnId={historyFocusId.current} testId="medical-order-history">
      {history !== null ? <OrderHistory scope={scope} orderId={history} onDenied={denied} /> : null}
    </Modal>
  </section>;
}

function OrderContentView({ version }: { version: OrderVersion }) {
  const { t } = useI18n();
  return <dl className="space-y-2 text-sm">
    {version.content.kind === "medication" ? medicationFields.map(field => <div key={field}>
      <dt className="font-semibold text-platforma-subtle">{t(`medical.orders.field.${field}`)}</dt>
      <dd className="whitespace-pre-wrap break-words">{version.content.medication[field] || t("medical.clinical.notRecorded")}</dd>
    </div>) : null}
    <div><dt className="font-semibold text-platforma-subtle">{t("medical.orders.text")}</dt>
      <dd className="whitespace-pre-wrap break-words">{version.content.text || t("medical.clinical.notRecorded")}</dd></div>
    {version.reason ? <div><dt className="font-semibold text-platforma-subtle">{t("medical.reason")}</dt><dd className="whitespace-pre-wrap break-words">{version.reason}</dd></div> : null}
  </dl>;
}

function OrderHistory({ scope, orderId, onDenied }: { scope: OrderScope; orderId: number; onDenied: (cause: unknown) => void }) {
  const { t, language } = useI18n();
  const [rows, setRows] = useState<OrderVersion[]>([]);
  const [cursor, setCursor] = useState<number | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [before, setBefore] = useState<number>();
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError(null);
    const { encounter_id: _, ...readScope } = scope;
    api.history(readScope, orderId, before, controller.signal).then(page => {
      if (!controller.signal.aborted) { setRows(previous => before ? [...previous, ...page.results] : page.results); setCursor(page.next_before_revision); }
    }).catch(cause => { if (!controller.signal.aborted) { if (medicalRoleDenied(cause)) onDenied(cause); else setError(cause); } })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [scope, orderId, before, attempt, onDenied]);
  return <div className="space-y-4">
    {loading ? <LoadingState /> : null}
    {error ? <ErrorState message={getApiErrorMessage(error)} action={<Button onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button>} /> : null}
    {rows.map(row => <article key={row.version_id} className="space-y-3 border-b border-platforma-border pb-4">
      <h3 className="text-base font-semibold">{t("medical.clinical.revision")} {row.revision} · {t(`medical.orders.${row.content.kind}`)}</h3>
      <p className="break-words text-sm text-platforma-subtle">{row.author_name} · {formatDateTime(row.created_at, undefined, true, localeByLanguage[language])}</p>
      <OrderContentView version={row} />
    </article>)}
    {cursor !== null ? <Button size="lg" disabled={loading} onClick={() => setBefore(cursor)}>{t("medical.clinical.older")}</Button> : null}
  </div>;
}

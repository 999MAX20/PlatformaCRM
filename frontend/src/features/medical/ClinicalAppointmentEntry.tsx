import { useQueryClient } from "@tanstack/react-query";
import { offerPurchaseAfterCompletion } from "../procurement/PurchasePrompt";
import type { PurchasePromptScope } from "../../api/medicalPurchasePrompt";
import { refreshAppointmentQueries } from "../../lib/appointmentCache";
import { ClinicalViewNavigationProvider } from "./clinicalViewNavigation";
import { useCallback, useEffect, useImperativeHandle, useMemo, useRef, useState, type Ref } from "react";
import axios from "axios";
import { medicalClinicalApi, type AppointmentClinicalContext } from "../../api/medicalClinical";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { Input } from "../../components/ui/Input";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { ClinicalDraftForm, type ClinicalDraftControl } from "./ClinicalDraftForm";
import { useUnsavedEntryWarning } from "../auth/useUnsavedEntryWarning";
import { Tabs } from "../../components/ui/Tabs";
import { ClinicalHistory } from "./ClinicalHistory";
import { ToothChart } from "./ToothChart";
import { SourceProposalEntry } from "./SourceProposalWorkspace";
import { AppointmentAssistants } from "./AppointmentAssistants";
import { DocumentWorkspace } from "./documents/DocumentWorkspace";
import { OrderWorkspace } from "./orders/OrderWorkspace";
import { ClinicalOverview } from "./ClinicalOverview";
import { ClinicalVisitPlans } from "./ClinicalVisitPlans";
import type { HistoryMemory } from "./clinicalHistoryNavigation";
import { useAuth } from "../auth/AuthProvider";
import { clinicalCardMemory, type ClinicalTab } from "./clinicalCardMemory";
import { MedicalFilesWorkspace, type MedicalFilesState, type MedicalFilesNavigation } from "./files/MedicalFilesWorkspace";

export type ClinicalEntryHandle = { beforeLeave: () => Promise<boolean> };

export function ClinicalAppointmentEntry({ businessId, appointmentId, embedded = false, navigationRef, onDirtyChange, onInitialAccessDenied }: {
  businessId: number; appointmentId: number; embedded?: boolean; navigationRef?: Ref<ClinicalEntryHandle>; onDirtyChange?: (dirty: boolean) => void; onInitialAccessDenied?: () => void;
}) {
  const { t } = useI18n();
  const { user } = useAuth();
  const cache = useQueryClient();
  const [completed, setCompleted] = useState(false);
  const memory = useMemo(() => clinicalCardMemory(`${businessId}:${user?.id}`, appointmentId), [businessId, user?.id, appointmentId]);
  const [tab, setTabState] = useState<ClinicalTab>(memory.tab);
  const setTab = (next: ClinicalTab) => { memory.tab = next; setTabState(next); };
  const historyMemory: HistoryMemory = useRef(memory.history);
  const [context, setContext] = useState<AppointmentClinicalContext | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(embedded);
  const [refresh, setRefresh] = useState(0);
  const [dirty, setDirty] = useState(false);
  const [fileState, setFileState] = useState<MedicalFilesState>({ dirty: false, pending: false });
  const fileGuard = useRef(fileState);
  const onFilesState = useCallback((value: MedicalFilesState) => { fileGuard.current = value; setFileState(value); }, []);
  const [confirmClose, setConfirmClose] = useState(false);
  const [closing, setClosing] = useState(false);
  const [closeFailed, setCloseFailed] = useState(false);
  const draftControl = useRef<ClinicalDraftControl>(null);
  const closeInFlight = useRef(false);
  const workspacePending = useRef(false);
  const onWorkspacePending = useCallback((value: boolean) => { workspacePending.current = value; }, []);
  const leaveRequest = useRef<((allowed: boolean) => void) | null>(null);
  const completionOffer = useRef<PurchasePromptScope | null>(null);
  const offerAfterLeave = useCallback(() => {
    const scope = completionOffer.current; completionOffer.current = null;
    if (scope) offerPurchaseAfterCompletion(scope);
  }, []);
  useEffect(() => () => offerAfterLeave(), [offerAfterLeave]);
  const documentEditor = useRef(false);
  const onDocumentEditor = useCallback((value: boolean) => { documentEditor.current = value; }, []);
  const canEditDocument = useCallback(() => !draftControl.current?.isPending(), []);
  const [admitted, setAdmitted] = useState(false);
  const admittedScope = useRef<string | null>(null);
  useUnsavedEntryWarning(dirty || fileState.dirty);
  useEffect(() => { onDirtyChange?.(dirty || fileState.dirty); }, [dirty, fileState.dirty, onDirtyChange]);
  const focusId = `clinical-open-${businessId}-${appointmentId}`;
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setContext(null); setError(null); setDirty(false);
    medicalClinicalApi.appointmentContext({ business_id: businessId, appointment_id: appointmentId }, controller.signal)
      .then(value => { if (!controller.signal.aborted) { setContext(value); setAdmitted(true); admittedScope.current = `${businessId}:${appointmentId}`; } })
      .catch(cause => {
        if (controller.signal.aborted) return;
        setError(cause);
        if (axios.isAxiosError(cause) && cause.response?.status === 403 && admittedScope.current !== `${businessId}:${appointmentId}`) onInitialAccessDenied?.();
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [businessId, appointmentId, refresh, open, onInitialAccessDenied]);
  const status = axios.isAxiosError(error) ? error.response?.status : undefined;
  function resolveLeave(allowed: boolean) {
    leaveRequest.current?.(allowed); leaveRequest.current = null;
  }
  const finishClose = () => { setConfirmClose(false); if (!embedded) setOpen(false); setDirty(false); resolveLeave(true); offerAfterLeave(); };
  const keepEditing = () => { setConfirmClose(false); resolveLeave(false); };
  useImperativeHandle(navigationRef, () => ({ beforeLeave: async () => {
    if (fileGuard.current.pending || (fileGuard.current.dirty && !window.confirm(t("medical.clinical.discard")))) return false;
    if (documentEditor.current || workspacePending.current || closeInFlight.current || draftControl.current?.isPending() || leaveRequest.current) return false;
    if (draftControl.current?.isDirty() && context?.encounter) {
      setCloseFailed(false); setConfirmClose(true);
      return new Promise<boolean>(resolve => { leaveRequest.current = resolve; });
    }
    const allowed = !dirty || window.confirm(t("medical.clinical.discard"));
    if (allowed) offerAfterLeave();
    return allowed;
  } }));
  useEffect(() => () => resolveLeave(false), []);
  const close = () => {
    if (fileGuard.current.pending || (fileGuard.current.dirty && !window.confirm(t("medical.clinical.discard")))) return;
    if (documentEditor.current || workspacePending.current || closeInFlight.current || draftControl.current?.isPending()) return;
    if (draftControl.current?.isDirty() && context?.encounter) { setCloseFailed(false); setConfirmClose(true); return; }
    if (dirty && !window.confirm(t("medical.clinical.discard"))) return;
    finishClose();
  };
  async function saveAndClose() {
    if (closeInFlight.current) return;
    closeInFlight.current = true; setClosing(true); setCloseFailed(false);
    try {
      if (await draftControl.current?.save()) finishClose();
      else setCloseFailed(true);
    } finally { closeInFlight.current = false; setClosing(false); }
  }
  const denied = useCallback((cause: unknown) => { setContext(null); setError(cause); setDirty(false); setConfirmClose(false); }, []);
  const reload = () => { setLoading(true); setContext(null); setError(null); setRefresh(value => value + 1); };
  const completedEncounter = () => {
    if (context?.encounter) completionOffer.current = { business_id: businessId, encounter_id: context.encounter.id };
    setContext(null); setDirty(false); setCompleted(true); setError(null);
    memory.tab = "overview";
    void refreshAppointmentQueries(cache);
  };
  const workspace = completed ? <p role="status" className="py-4 text-sm" data-testid="encounter-completed">{t("medical.completion.done")}</p> : loading ? <LoadingState /> : error ? <ErrorState message={status === 401 || status === 403 ? t("medical.denied") : getApiErrorMessage(error)}
    action={<Button size="lg" variant="secondary" onClick={reload}>{t("common.retry")}</Button>} /> : context ?
    <ClinicalWorkspace onCompleted={completedEncounter} compact={embedded} onPending={onWorkspacePending} historyMemory={historyMemory} tab={tab} onTabChange={setTab} draftControl={draftControl} context={context} onChanged={reload} onDirty={setDirty} onDenied={denied}
      onDocumentEditor={onDocumentEditor} canEditDocument={canEditDocument} onFilesState={onFilesState} /> : null;
  if (!open && (status === 401 || status === 403)) return null;
  return <div className="mt-4" data-testid="clinical-appointment-entry">
    {loading && !open ? <LoadingState /> : !open && error ? <ErrorState
      message={status === 404 ? t("medical.clinical.noProfile") : getApiErrorMessage(error)}
      action={<Button size="lg" variant="secondary" onClick={reload}>{t("common.retry")}</Button>} /> : null}
    {!embedded ? <div className="flex flex-wrap gap-2">{admitted ? <Button size="lg" variant="secondary" data-focus-return-id={focusId} onClick={() => {
      setLoading(true); setContext(null); setError(null); setOpen(true);
    }}>{t("medical.clinical.open")}</Button> : null}
    {context ? <SourceProposalEntry scope={{ business_id: businessId, patient_id: context.patient.id, source_appointment_id: appointmentId }} /> : null}</div> : null}
    <ClinicalViewNavigationProvider sharedMemory={memory.views}>{embedded ? <section data-testid="clinical-workspace">{workspace}</section> :
      <Modal open={open} onClose={close} size="xl" title={t("medical.clinical.title")} testId="clinical-workspace" closeOnBackdrop={false} focusReturnId={focusId}>{workspace}</Modal>}
    </ClinicalViewNavigationProvider>
    <Modal open={confirmClose && open} onClose={() => { if (!closeInFlight.current) keepEditing(); }}
      title={t("medical.clinical.unsavedTitle")} size="sm" closeOnBackdrop={false} testId="clinical-unsaved">
      <div className="space-y-4">
        {closeFailed ? <p role="alert" className="text-sm text-platforma-text">{t("medical.clinical.closeFailed")}</p> : null}
        <div className="flex flex-wrap gap-3">
          <Button size="lg" isLoading={closing} onClick={() => void saveAndClose()}>{t("medical.clinical.saveClose")}</Button>
          <Button size="lg" variant="secondary" disabled={closing} onClick={keepEditing}>{t("medical.clinical.continueEditing")}</Button>
          <Button size="lg" variant="secondary" disabled={closing} onClick={finishClose}>{t("medical.clinical.leaveUnsaved")}</Button>
        </div>
      </div>
    </Modal>
  </div>;
}

function ClinicalWorkspace({ onCompleted, context, onChanged, onDirty, onDenied, draftControl, onDocumentEditor, canEditDocument, tab, onTabChange, historyMemory, compact = false, onPending, onFilesState }: {
  onCompleted: () => void;
  onFilesState: (state: MedicalFilesState) => void;
  compact?: boolean;
  onPending: (pending: boolean) => void;
  historyMemory: HistoryMemory;
  tab: ClinicalTab; onTabChange: (tab: ClinicalTab) => void;
  onDocumentEditor: (open: boolean) => void; canEditDocument: () => boolean;
  draftControl: Ref<ClinicalDraftControl>;
  context: AppointmentClinicalContext; onChanged: () => void; onDirty: (value: boolean) => void; onDenied: (cause: unknown) => void;
}) {
  const { t } = useI18n();
  const [number, setNumber] = useState("");
  const tabPrefix = `clinical-${context.appointment.id}`;
  const planScope = useMemo(() => ({ business_id: context.business_id, patient_id: context.patient.id,
    appointment_id: context.appointment.id }), [context]);
  const fileScope = useMemo(() => context.active_record ? { ...planScope, record_id: context.active_record.id,
    encounter_id: context.encounter?.id } : null, [context, planScope]);
  const filesNavigation = useRef<MedicalFilesNavigation>(null);
  const [pending, setPending] = useState(false);
  const [assistantPending, setAssistantPending] = useState(false);
  useEffect(() => { onPending(pending || assistantPending); return () => onPending(false); }, [pending, assistantPending, onPending]);
  const [error, setError] = useState<unknown>(null);
  const request = useRef<{ fingerprint: string; key: string } | null>(null);
  const controller = useRef(new AbortController());
  useEffect(() => { const active = new AbortController(); controller.current = active; return () => active.abort(); }, []);
  async function create() {
    if (pending) return;
    const scope = { business_id: context.business_id, patient_id: context.patient.id, appointment_id: context.appointment.id };
    const payload = context.active_record ? { ...scope, record_id: context.active_record.id,
      expected_patient_revision: context.patient.revision, expected_appointment_updated_at: context.appointment.updated_at } :
      { ...scope, number, expected_patient_revision: context.patient.revision };
    const fingerprint = JSON.stringify(payload);
    if (request.current?.fingerprint !== fingerprint) request.current = { fingerprint, key: crypto.randomUUID() };
    setPending(true); setError(null);
    const signal = controller.current.signal;
    try {
      if ("record_id" in payload) await medicalClinicalApi.openEncounter(payload, request.current.key, signal);
      else await medicalClinicalApi.openRecord(payload, request.current.key, signal);
      if (!signal.aborted) { onDirty(false); onChanged(); }
    } catch (cause) {
      if (!signal.aborted) {
        if (axios.isAxiosError(cause) && [401, 403].includes(cause.response?.status ?? 0)) onDenied(cause);
        else setError(cause);
      }
    } finally { if (!signal.aborted) setPending(false); }
  }
  return <div className="min-w-0 space-y-4">
    <aside className="flex min-w-0 flex-wrap items-center gap-x-5 gap-y-2 border-b border-platforma-border pb-3">
      {!compact ? <h2 className="break-words text-lg font-semibold text-platforma-text">{context.patient.full_name}</h2> : null}
      <p className="text-sm text-platforma-subtle">{t(`medical.${context.patient.identity_status}`)}</p>
      {context.active_record ? <p className="break-words text-sm">{t("medical.clinical.number")}: {context.active_record.number}</p> : null}
      {context.patient.identity_status !== "verified" ? <p role="status" className="text-sm text-platforma-subtle">{t("medical.clinical.verifyFirst")}</p> : null}
      {compact ? <SourceProposalEntry scope={{ business_id: context.business_id, patient_id: context.patient.id, source_appointment_id: context.appointment.id }} /> : null}
    </aside>
    <AppointmentAssistants key={`${context.business_id}:${context.appointment.id}`} scope={planScope} onPending={setAssistantPending} />
    <div className="min-w-0 space-y-4">
      <Tabs value={tab} onChange={onTabChange} idPrefix={tabPrefix} ariaLabel={t("medical.clinical.title")}
        className="[&_[role=tab]]:min-h-11" appearance="underline"
        options={[{ value: "overview", label: t("medical.overview.title") }, { value: "encounter", label: t("medical.clinical.note") }, { value: "history", label: t("medical.clinical.history") }, { value: "teeth", label: t("medical.tooth.title") },
          { value: "plan", label: t("medical.clinical.plan") }, { value: "files", label: t("medical.files.title") }, { value: "documents", label: t("medical.documents.title") }, { value: "orders", label: t("medical.orders.title") }]} />
      <div role="tabpanel" id={`${tabPrefix}-panel-overview`} aria-labelledby={`${tabPrefix}-tab-overview`} hidden={tab !== "overview"}>
        {tab === "overview" ? <ClinicalOverview context={context} onDenied={onDenied} onNavigate={next => {
          onTabChange(next);
          requestAnimationFrame(() => document.getElementById(`${tabPrefix}-tab-${next}`)?.focus());
        }} /> : null}
      </div>
      <div role="tabpanel" id={`${tabPrefix}-panel-${tab === "plan" ? "encounter" : "plan"}`} aria-labelledby={`${tabPrefix}-tab-${tab === "plan" ? "encounter" : "plan"}`} hidden />
      <div role="tabpanel" id={`${tabPrefix}-panel-${tab === "plan" ? "plan" : "encounter"}`} aria-labelledby={`${tabPrefix}-tab-${tab === "plan" ? "plan" : "encounter"}`} hidden={tab !== "encounter" && tab !== "plan"} className="space-y-4">
      {tab === "plan" ? <ClinicalVisitPlans scope={planScope} entry="plan" /> : null}
      {context.encounter ? <ClinicalDraftForm onCompleted={onCompleted} view={tab === "plan" ? "plan" : "encounter"} draftControl={draftControl} context={context} onDirty={onDirty} onDenied={onDenied} onReload={onChanged} /> : <>
        <p className="text-sm text-platforma-subtle">{t(context.active_record ? "medical.clinical.noEncounter" : "medical.clinical.noRecord")}</p>
        {context.actions.create_record ? <Input label={t("medical.clinical.number")} value={number} maxLength={64} disabled={pending}
          onChange={event => { setNumber(event.target.value); onDirty(Boolean(event.target.value)); }} /> : null}
        {context.actions.create_record || context.actions.open_encounter ? <Button size="lg" isLoading={pending}
          disabled={context.actions.create_record && !number.trim()} onClick={() => void create()}>
          {t(context.active_record ? "medical.clinical.start" : "medical.clinical.createRecord")}</Button> : null}
        {error ? <ErrorState message={getApiErrorMessage(error)} action={axios.isAxiosError(error) && error.response?.status === 409 ?
          <Button size="lg" variant="secondary" onClick={() => {
            if (!number || window.confirm(t("medical.clinical.discard"))) onChanged();
          }}>{t("medical.clinical.reload")}</Button> : undefined} /> : null}
      </>}
      </div>
      <div role="tabpanel" id={`${tabPrefix}-panel-teeth`} aria-labelledby={`${tabPrefix}-tab-teeth`} hidden={tab !== "teeth"}>
        {tab === "teeth" ? <ToothChart context={context} onDenied={onDenied} onFiles={fileScope ? tooth => {
          if (!filesNavigation.current?.openTooth(tooth)) return;
          onTabChange("files");
          requestAnimationFrame(() => document.getElementById(`${tabPrefix}-tab-files`)?.focus());
        } : undefined} /> : null}
      </div>
      <div role="tabpanel" id={`${tabPrefix}-panel-history`} aria-labelledby={`${tabPrefix}-tab-history`} hidden={tab !== "history"}>
        {tab === "history" ? <ClinicalHistory context={context} onDenied={onDenied} memory={historyMemory} /> : null}
      </div>
      <div role="tabpanel" id={`${tabPrefix}-panel-documents`} aria-labelledby={`${tabPrefix}-tab-documents`} hidden={tab !== "documents"}>
        {context.encounter ? <DocumentWorkspace context={context} active={tab === "documents"} onEditor={onDocumentEditor} canEdit={canEditDocument} /> :
          <p className="text-sm text-platforma-subtle">{t("medical.clinical.noEncounter")}</p>}
      </div>
      <div role="tabpanel" id={`${tabPrefix}-panel-orders`} aria-labelledby={`${tabPrefix}-tab-orders`} hidden={tab !== "orders"}>
        {context.encounter ? <OrderWorkspace context={context} active={tab === "orders"} onEditor={onDocumentEditor} canEdit={canEditDocument} /> :
          <p className="text-sm text-platforma-subtle">{t("medical.clinical.noEncounter")}</p>}
      </div>
      <div role="tabpanel" id={`${tabPrefix}-panel-files`} aria-labelledby={`${tabPrefix}-tab-files`} hidden={tab !== "files"}>
        {fileScope ? <MedicalFilesWorkspace scope={fileScope} active={tab === "files"} onState={onFilesState} onDenied={onDenied} navigationRef={filesNavigation} /> :
          <p className="text-sm text-platforma-subtle">{t("medical.clinical.noRecord")}</p>}
      </div>
    </div>
  </div>;
}

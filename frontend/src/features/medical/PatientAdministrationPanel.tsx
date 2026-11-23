import { useCallback, useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { branchesApi } from "../../api/branches";
import { medicalPatientsApi, type PatientAdministration, type PatientAdministrationAccess, type PatientScope } from "../../api/medicalPatients";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Select } from "../../components/ui/Select";
import { Modal } from "../../components/ui/Modal";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { PatientIdentityForm, type PatientEditMode } from "./PatientIdentityForm";
import { PatientRepresentatives } from "./PatientRepresentatives";
import { PatientParticipationEntry } from "./ParticipationEntry";
import { PatientIdentityCorrections } from "./PatientIdentityCorrections";
import { CorrectionAccessPanel } from "./CorrectionAccessPanel";
import { ClientClinicalEntry } from "./ClientClinicalEntry";
import { ActualVisitEntry } from "./ActualVisitEntry";
import { DocumentIssuanceEntry } from "./DocumentIssuanceEntry";

export function PatientAdministrationPanel({ businessId, clientId, clientName, userId }: { businessId: number; clientId: number; clientName: string; userId: number }) {
  const { t } = useI18n();
  const [branch, setBranch] = useState("");
  const [identityRefresh, setIdentityRefresh] = useState(0);
  const [revoked, setRevoked] = useState(false);
  const onIdentityChanged = useCallback(() => setIdentityRefresh(value => value + 1), []);
  const onDenied = useCallback(() => setRevoked(true), []);
  const branches = useQuery({ queryKey: ["medical-branch-options", businessId, userId], queryFn: () => branchesApi.listAll({ business: businessId }) });
  const available = (branches.data ?? []).filter(item => item.is_active && !item.archived_at && item.can_work);
  const selected = branch || (available.length === 1 ? String(available[0].id) : "");
  const valid = available.some(item => String(item.id) === selected);
  return <section className="space-y-4 rounded-card border border-platforma-border bg-surface-card p-4 sm:p-5 lg:col-span-2" aria-label={t("medical.title")} data-testid="patient-administration">
    <h2 className="text-base font-semibold text-platforma-text">{t("medical.title")}</h2>
    {branches.isLoading ? <LoadingState /> : branches.error ? <ErrorState message={getApiErrorMessage(branches.error)} action={<Button variant="secondary" onClick={() => void branches.refetch()}>{t("common.retry")}</Button>} /> : <>
      <Select label={t("medical.branch")} value={selected} onChange={event => { setBranch(event.target.value); setRevoked(false); }} options={[
        { value: "", label: t("medical.selectBranch") }, ...available.map(item => ({ value: item.id, label: item.name })),
      ]} />
      {valid && revoked ? <ErrorState message={t("medical.denied")} action={<Button variant="secondary" onClick={() => { setRevoked(false); onIdentityChanged(); }}>{t("common.retry")}</Button>} /> : valid ? <>
        <DocumentIssuanceEntry key={`issue:${businessId}:${clientId}:${selected}`} businessId={businessId} clientId={clientId} branchId={Number(selected)} />
        <ActualVisitEntry key={`actual:${businessId}:${clientId}:${selected}`} scope={{ business_id: businessId, client_id: clientId, branch_id: Number(selected) }} />
        <ClientClinicalEntry key={`clinical-entry:${businessId}:${clientId}:${userId}:${selected}`} businessId={businessId} clientId={clientId} branchId={Number(selected)} />
        <PatientParticipationEntry key={`participation:${businessId}:${clientId}:${userId}:${selected}`} businessId={businessId} clientId={clientId} branchId={Number(selected)} />
        <CorrectionAccessPanel key={`clinical-corrections:${businessId}:${clientId}:${userId}:${selected}`} scope={{ business_id: businessId, branch_id: Number(selected), client_id: clientId }} />
        <PatientInBranch key={`${businessId}:${clientId}:${userId}:${selected}`} clientId={clientId} clientName={clientName} scope={{ business_id: businessId, branch_id: Number(selected) }} onIdentityChanged={onIdentityChanged} onAccessDenied={onDenied} />
        <PatientIdentityCorrections key={`corrections:${businessId}:${clientId}:${userId}:${selected}:${identityRefresh}`} clientId={clientId} scope={{ business_id: businessId, branch_id: Number(selected) }} onDenied={onDenied} />
      </> : <p className="text-sm text-platforma-subtle">{t("medical.selectBranch")}</p>}
    </>}
  </section>;
}

function PatientInBranch({ scope, clientId, clientName, onIdentityChanged, onAccessDenied }: { scope: PatientScope; clientId: number; clientName: string; onIdentityChanged: () => void; onAccessDenied: () => void }) {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [patient, setPatient] = useState<PatientAdministration | null>(null);
  const [access, setAccess] = useState<PatientAdministrationAccess | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [refresh, setRefresh] = useState(0);
  const [mode, setMode] = useState<PatientEditMode | null>(null);
  const [saved, setSaved] = useState(false);
  const [admitted, setAdmitted] = useState(false);
  const [formState, setFormState] = useState({ dirty: false, pending: false });
  function close() {
    if (mode === "correctIin" && (formState.pending || (formState.dirty && !window.confirm(t("medical.clinical.discard"))))) return;
    setMode(null); setFormState({ dirty: false, pending: false });
  }
  function denied() {
    setMode(null); setPatient(null); setAccess(null); setLoading(false);
    setError(new Error("medical_access_revoked"));
    onAccessDenied();
  }
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(null); setPatient(null); setAccess(null);
    async function load() {
      try {
        const permissions = await medicalPatientsApi.access(scope, controller.signal);
        if (!controller.signal.aborted) setAdmitted(true);
        let result: PatientAdministration | null;
        try { result = await medicalPatientsApi.byClient(clientId, scope, controller.signal); }
        catch (cause) {
          if (axios.isAxiosError(cause) && cause.response?.status === 404) result = null;
          else throw cause;
        }
        if (!controller.signal.aborted) { setAccess(permissions); setPatient(result); }
      } catch (cause) { if (!controller.signal.aborted) setError(cause); }
      finally { if (!controller.signal.aborted) setLoading(false); }
    }
    void load();
    return () => controller.abort();
  }, [scope.business_id, scope.branch_id, clientId, refresh]);
  if (loading) return <LoadingState />;
  if (!admitted && axios.isAxiosError(error) && error.response?.status === 403) return null;
  if (error) return <ErrorState message={error instanceof Error && error.message === "medical_access_revoked" ? t("medical.denied") : getApiErrorMessage(error)} action={<Button variant="secondary" onClick={() => setRefresh(value => value + 1)}>{t("common.retry")}</Button>} />;
  const actions = access?.actions;
  return <div className="space-y-4">
    {saved ? <p role="status" className="text-sm text-platforma-text">{t("common.saved")}</p> : null}
    {patient ? <>
      <p className="text-sm font-semibold text-platforma-text">{t(`medical.${patient.identity_status}`)}</p>
      <dl className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2">
        {[["fullName", patient.full_name], ["birth", patient.demographics.date_of_birth], ["sex", patient.demographics.sex], ["address", patient.demographics.address]].map(([key, value]) => <div key={key} className="min-w-0"><dt className="text-platforma-subtle">{t(`medical.${key}`)}</dt><dd className="mt-1 whitespace-pre-wrap break-words text-platforma-text">{value || "—"}</dd></div>)}
      </dl>
      <div className="flex flex-wrap gap-2">
        {actions?.update && patient.identity_status === "unverified" ? <Button size="lg" variant="secondary" onClick={() => setMode("preliminary")}>{t("medical.edit")}</Button> : null}
        {actions?.approve && patient.identity_status === "unverified" ? <Button size="lg" onClick={() => setMode("verify")}>{t("medical.verify")}</Button> : null}
        {actions?.approve && actions.update && patient.identity_status === "verified" ? <Button size="lg" variant="secondary" onClick={() => setMode("correct")}>{t("medical.correct")}</Button> : null}
        {actions?.approve && actions.update && patient.identity_status === "verified" ? <Button size="lg" variant="secondary" onClick={() => { setFormState({ dirty: false, pending: false }); setMode("correctIin"); }}>{t("medical.correctIin")}</Button> : null}
      </div>
      <PatientRepresentatives patient={patient} scope={scope} canApprove={!!actions?.approve} onDenied={denied} />
    </> : <>
      <p className="text-sm text-platforma-subtle">{t("medical.empty")}</p>
      {actions?.create ? <Button size="lg" onClick={() => setMode("create")}>{t("medical.create")}</Button> : null}
    </>}
    <Modal title={t(`medical.${mode ?? "title"}`)} open={mode !== null} onClose={close} size="lg" closeOnBackdrop={false}>
      {mode ? <PatientIdentityForm key={mode} mode={mode} patient={patient} clientId={clientId} clientName={clientName} scope={scope} onDenied={denied}
        onDraft={mode === "correctIin" ? setFormState : undefined}
        onCancel={() => { close(); if (mode !== "correctIin") setRefresh(value => value + 1); }}
        onSaved={() => {
          setMode(null); setSaved(true); setRefresh(value => value + 1);
          onIdentityChanged();
          void queryClient.invalidateQueries({ queryKey: ["crm-card", "client", clientId, scope.business_id] });
          void queryClient.invalidateQueries({ queryKey: ["clients"] });
        }} /> : null}
    </Modal>
  </div>;
}

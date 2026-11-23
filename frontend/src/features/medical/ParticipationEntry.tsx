import { ClinicalViewNavigationProvider } from "./clinicalViewNavigation";
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import { medicalParticipationApi as api, type Participation, type ParticipationPage, type ParticipationWorkspaceAccess } from "../../api/medicalParticipation";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { Select } from "../../components/ui/Select";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { ParticipationCommandForm, type ParticipationFormScope } from "./ParticipationCommandForm";
import { ParticipationClinicalHistory } from "./ClinicalHistory";
import { ParticipationClinicalOverview } from "./ClinicalOverview";
import { ParticipationToothChart } from "./ToothChart";
import { SourceProposalWorkspace } from "./SourceProposalWorkspace";
import { ParticipationDeclineForm } from "./ParticipationDeclineForm";
import { ParticipationInvitationDetails } from "./ParticipationInvitationDetails";
import { ParticipationClosurePanel } from "./ParticipationClosurePanel";
import type { HistoryMemory } from "./clinicalHistoryNavigation";
import { MedicalFilesWorkspace, type MedicalFilesState } from "./files/MedicalFilesWorkspace";
import type { MedicalFileWorkspaceScope } from "../../api/medicalFiles";

export function PatientParticipationEntry({ businessId, clientId, branchId }: { businessId: number; clientId: number; branchId: number }) {
  const { t } = useI18n();
  const [patientId, setPatientId] = useState<number | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setPatientId(null); setError(null);
    void api.patientContext({ business_id: businessId, client_id: clientId, branch_id: branchId }, controller.signal)
      .then(value => { if (!controller.signal.aborted) setPatientId(value.patient_id); })
      .catch(cause => { if (!controller.signal.aborted) setError(cause); });
    return () => controller.abort();
  }, [businessId, clientId, branchId, attempt]);
  if (error && (!axios.isAxiosError(error) || ![401, 403, 404].includes(error.response?.status ?? 0))) {
    return <ErrorState message={getApiErrorMessage(error)} action={<Button variant="secondary" onClick={() => setAttempt(x => x + 1)}>{t("common.retry")}</Button>} />;
  }
  if (!patientId && !error) return <LoadingState />;
  return patientId ? <ParticipationEntry businessId={businessId} patientId={patientId} branchId={branchId} /> : null;
}

export function ParticipationEntry({ businessId, patientId, branchId, onClosed }: { businessId: number; patientId?: number; branchId?: number; onClosed?: () => void }) {
  const { t } = useI18n();
  const [access, setAccess] = useState<ParticipationWorkspaceAccess | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [open, setOpen] = useState(false);
  const [admitted, setAdmitted] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const guard = useRef({ dirty: false, pending: false });
  const historyMemory: HistoryMemory = useRef(new Map());
  const denied = useCallback((cause: unknown) => { setAccess(null); setAdmitted(false); setError(cause); guard.current = { dirty: false, pending: false }; }, []);
  useEffect(() => {
    const controller = new AbortController();
    setAccess(null); setError(null);
    void api.access(businessId, controller.signal).then(value => { if (!controller.signal.aborted) { setAccess(value); setAdmitted(true); } })
      .catch(cause => { if (!controller.signal.aborted) {
        setError(cause);
        if (axios.isAxiosError(cause) && [401, 403].includes(cause.response?.status ?? 0)) setAdmitted(false);
      } });
    return () => controller.abort();
  }, [businessId, open, attempt]);
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => { if (guard.current.dirty || guard.current.pending) { event.preventDefault(); event.returnValue = ""; } };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, []);
  const forbidden = axios.isAxiosError(error) && [401, 403].includes(error.response?.status ?? 0);
  if (forbidden && !open) return null;
  const focusId = `participation-${businessId}-${patientId ?? "mine"}`;
  return <>
    {admitted ? <Button id={focusId} size="lg" variant="secondary" onClick={() => setOpen(true)}>{t("medical.participation.title")}</Button> : null}
    {error && !forbidden && !open ? <ErrorState message={getApiErrorMessage(error)} action={<Button variant="secondary" onClick={() => setAttempt(x => x + 1)}>{t("common.retry")}</Button>} /> : null}
    <ClinicalViewNavigationProvider><Modal title={t("medical.participation.title")} open={open} size="xl" closeOnBackdrop={false} focusReturnId={focusId}
      onClose={() => { if (!guard.current.pending && (!guard.current.dirty || window.confirm(t("medical.clinical.discard")))) { guard.current.dirty = false; setOpen(false); onClosed?.(); } }}>
      {error ? <ErrorState message={forbidden ? t("medical.denied") : getApiErrorMessage(error)} action={<Button variant="secondary" onClick={() => setAttempt(x => x + 1)}>{t("common.retry")}</Button>} /> : access ?
        <ParticipationWorkspace historyMemory={historyMemory} key={`${businessId}:${patientId ?? "mine"}:${branchId ?? "all"}`} access={access} patientId={patientId} branchId={branchId} guard={guard} onDenied={denied} /> : <LoadingState />}
    </Modal></ClinicalViewNavigationProvider>
  </>;
}

function ParticipationWorkspace({ access, patientId, branchId, guard, onDenied, historyMemory }: {
  historyMemory: HistoryMemory;
  access: ParticipationWorkspaceAccess; patientId?: number; branchId?: number;
  guard: { current: { dirty: boolean; pending: boolean } }; onDenied: (cause: unknown) => void;
}) {
  const { t } = useI18n();
  const [mode, setMode] = useState<"mine" | "managed">(patientId && access.kind === "head" ? "managed" : "mine");
  const [branch, setBranch] = useState(String(branchId ?? access.branches[0]?.id ?? ""));
  const [cursor, setCursor] = useState<number | undefined>();
  const [page, setPage] = useState<ParticipationPage | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  const [form, setForm] = useState<Participation | "invite" | null>(null);
  const [history, setHistory] = useState<Participation | null>(null);
  const [overview, setOverview] = useState<Participation | null>(null);
  const [teeth, setTeeth] = useState<Participation | null>(null);
  const [proposal, setProposal] = useState<Participation | null>(null);
  const [files, setFiles] = useState<{ scope: MedicalFileWorkspaceScope; patientName?: string; branchName: string; returnId: string } | null>(null);
  const onFilesState = useCallback((state: MedicalFilesState) => { guard.current = state; }, [guard]);
  const [declining, setDeclining] = useState<Participation | null>(null);
  const [ownEnd, setOwnEnd] = useState<Participation | null>(null);
  const [pending, setPending] = useState<number | null>(null);
  const [conflict, setConflict] = useState(false);
  const retry = useRef<{ fingerprint: string; key: string } | null>(null);
  const workspaceRef = useRef<HTMLElement>(null);
  const clinicalRef = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => { clinicalRef.current?.focus(); }, [overview, history, teeth]);
  const focusAfterRefresh = useRef<string | null>(null);
  const chosen = access.branches.find(row => String(row.id) === branch);
  const scope = useMemo<ParticipationFormScope>(() => ({ businessId: access.business_id,
    patientId: typeof form === "object" && form ? form.patient_id : patientId!, branchId: Number(branch) }),
  [access.business_id, branch, form, patientId]);
  useEffect(() => {
    const controller = new AbortController();
    setPage(null); setError(null); setHistory(null); setOverview(null); setTeeth(null); setConflict(false);
    const pagination = { business_id: access.business_id, before_id: cursor };
    if (mode === "managed" && !chosen) { setPage({ results: [], next_before_id: null }); return () => controller.abort(); }
    const read = mode === "managed" ? api.managed({ ...pagination, branch_id: Number(branch), patient_id: patientId }, controller.signal) : api.mine(pagination, controller.signal);
    void read.then(value => { if (!controller.signal.aborted) setPage(value); }).catch(cause => {
      if (controller.signal.aborted) return;
      if (axios.isAxiosError(cause) && [401, 403].includes(cause.response?.status ?? 0)) onDenied(cause);
      else setError(cause);
    });
    return () => controller.abort();
  }, [access.business_id, mode, branch, patientId, cursor, attempt, chosen, onDenied]);
  useLayoutEffect(() => {
    if (!form && !proposal && !declining && !files && page && pending === null && focusAfterRefresh.current) {
      const target = workspaceRef.current?.querySelector<HTMLElement>(`[data-participation-focus="${focusAfterRefresh.current}"]`);
      if (target) { target.focus(); focusAfterRefresh.current = null; }
    }
  }, [form, proposal, declining, files, page, pending]);
  function refresh() {
    if (ownEnd) focusAfterRefresh.current = String(ownEnd.id);
    setOwnEnd(null);
    if (declining) focusAfterRefresh.current = String(declining.id);
    setDeclining(null);
    if (form) focusAfterRefresh.current = form === "invite" ? "invite" : String(form.id);
    setForm(null); setPage(null); setHistory(null); setOverview(null); setTeeth(null); guard.current.dirty = false; setAttempt(x => x + 1);
  }
  async function respond(item: Participation, decision: "accept" | "decline" | "withdraw") {
    if (guard.current.pending || conflict) return;
    guard.current.pending = true; setPending(item.id); setError(null);
    const payload = { business_id: access.business_id, patient_id: item.patient_id, expected_revision: item.revision };
    const fingerprint = JSON.stringify({ id: item.id, decision, ...payload });
    if (retry.current?.fingerprint !== fingerprint) retry.current = { fingerprint, key: crypto.randomUUID() };
    try {
      if (decision === "withdraw") await api.withdraw(item.id, payload, retry.current.key);
      else await api.respond(item.id, { ...payload, decision }, retry.current.key);
      focusAfterRefresh.current = String(item.id);
      refresh();
    } catch (cause) {
      if (axios.isAxiosError(cause) && [401, 403].includes(cause.response?.status ?? 0)) onDenied(cause);
      else { setError(cause); if (axios.isAxiosError(cause) && cause.response?.status === 409) setConflict(true); }
    } finally { guard.current.pending = false; setPending(null); }
  }
  if (ownEnd) return <div className="space-y-4">
    <p className="break-words font-semibold">{ownEnd.patient_name} · {ownEnd.branch_name}</p>
    <ParticipationClosurePanel businessId={access.business_id} item={ownEnd} own guard={guard} onSaved={refresh} onDenied={onDenied} />
    <Button size="lg" variant="secondary" onClick={() => { if (!guard.current.pending) refresh(); }}>{t("common.back")}</Button>
  </div>;
  if (files) return <div className="space-y-4">
    <Button autoFocus size="lg" variant="secondary" onClick={() => {
      if (guard.current.pending || (guard.current.dirty && !window.confirm(t("medical.clinical.discard")))) return;
      focusAfterRefresh.current = files.returnId; setFiles(null);
    }}>{t("common.back")}</Button>
    <p className="break-words font-semibold">{[files.patientName, files.branchName].filter(Boolean).join(" · ")}</p>
    <MedicalFilesWorkspace scope={files.scope} active onState={onFilesState} onDenied={onDenied} />
  </div>;
  if (declining) return <div className="space-y-4">
    <p className="break-words font-semibold">{declining.patient_name}</p>
    <ParticipationDeclineForm businessId={access.business_id} item={declining} guard={guard} onSaved={refresh} onDenied={onDenied}
      onCancel={() => { focusAfterRefresh.current = String(declining.id); setDeclining(null); }} />
  </div>;
  if (proposal) return <div className="space-y-4">
    <h3 className="text-base font-semibold">{t("medical.participation.proposals")}</h3>
    <p className="break-words text-sm">{proposal.patient_name}</p>
    <SourceProposalWorkspace scope={{ business_id: access.business_id, patient_id: proposal.patient_id, source_participation_id: proposal.id }}
      guard={guard} onDenied={onDenied} onBack={() => { focusAfterRefresh.current = String(proposal.id); setProposal(null); }} />
  </div>;
  if (form) return <div className="space-y-4">
    <h3 className="text-base font-semibold">{t(form === "invite" ? "medical.participation.invite" : "medical.participation.end")}</h3>
    {form !== "invite" ? <p className="break-words text-sm">{form.patient_name} · {form.member_name} · {form.branch_name}</p> : null}
    {form !== "invite" ? <ParticipationClosurePanel businessId={access.business_id} item={form} own={false} guard={guard} onSaved={refresh} onDenied={onDenied} /> : null}
    <ParticipationCommandForm scope={scope} item={form === "invite" ? undefined : form} guard={guard} onSaved={refresh} onDenied={onDenied} />
    <Button variant="secondary" onClick={() => { if (!guard.current.pending && (!guard.current.dirty || window.confirm(t("medical.clinical.discard")))) refresh(); }}>{t("common.cancel")}</Button>
  </div>;
  return <section ref={workspaceRef} className="space-y-4" data-testid="participation-workspace">
    {access.kind === "head" ? <Select label={t("medical.participation.list")} value={mode} disabled={pending !== null} onChange={event => { setCursor(undefined); setMode(event.target.value as "mine" | "managed"); }}
      options={[{ value: "mine", label: t("medical.participation.mine") }, { value: "managed", label: t("medical.participation.managed") }]} /> : null}
    {mode === "managed" ? <Select label={t("medical.branch")} value={branch} disabled={pending !== null} onChange={event => { setCursor(undefined); setBranch(event.target.value); }}
      options={access.branches.map(row => ({ value: row.id, label: row.name }))} /> : null}
    {mode === "managed" && patientId && chosen?.actions.create ? <Button data-participation-focus="invite" size="lg" disabled={pending !== null || conflict} onClick={() => setForm("invite")}>{t("medical.participation.invite")}</Button> : null}
    {mode === "managed" && patientId && chosen ? <Button data-participation-focus="files" size="lg" variant="secondary" disabled={pending !== null || conflict}
      onClick={() => setFiles({ scope: { business_id: access.business_id, patient_id: patientId, head_branch_id: chosen.id },
        branchName: chosen.name, returnId: "files" })}>{t("medical.files.title")}</Button> : null}
    <Button variant="secondary" disabled={pending !== null} onClick={refresh}>{t("medical.clinical.reload")}</Button>
    {error ? <ErrorState message={conflict ? t("medical.clinical.conflict") : getApiErrorMessage(error)} action={!page ? <Button variant="secondary" onClick={refresh}>{t("common.retry")}</Button> : undefined} /> : null}
    {!page && !error ? <LoadingState /> : null}
    {page && !page.results.length ? <p className="text-sm text-platforma-subtle">{t("medical.participation.empty")}</p> : null}
    <ul className="divide-y divide-platforma-border">
      {page?.results.map(item => {
        const actions = access.branches.find(row => row.id === item.branch_id)?.actions;
        return <li key={item.id} tabIndex={-1} className="space-y-3 py-4" data-participation-focus={item.id} data-testid={`participation-row-${item.id}`}>
          <div className="space-y-1 break-words"><p className="font-semibold">{item.patient_name}</p><p className="text-sm">{item.member_name} · {item.branch_name}</p>
            <p className="text-sm text-platforma-subtle">{t(`medical.participation.state.${item.state}`)}</p>
            {item.decline_reason ? <p className="whitespace-pre-wrap text-sm">{t("medical.participation.declineReason")}: {item.decline_reason}</p> : null}</div>
          <ParticipationInvitationDetails item={item} />
          <div className="flex flex-wrap gap-2">
            {item.state === "pending" && item.member_id === access.member_id && actions?.approve ? <>
              <Button size="lg" disabled={pending !== null || conflict} onClick={() => void respond(item, "accept")}>{t("medical.participation.accept")}</Button>
              <Button size="lg" variant="secondary" disabled={pending !== null || conflict} onClick={() => setDeclining(item)}>{t("medical.participation.decline")}</Button>
            </> : null}
            {item.state === "pending" && mode === "managed" && actions?.manage && actions.create ? <Button variant="secondary" disabled={pending !== null || conflict} onClick={() => void respond(item, "withdraw")}>{t("medical.participation.withdraw")}</Button> : null}
            {item.state === "active" && actions?.manage ? <Button size="lg" variant="secondary" disabled={pending !== null || conflict} onClick={() => setForm(item)}>{t("medical.participation.end")}</Button> : null}
            {item.state === "active" && item.member_id === access.member_id ? <>
              {actions?.update ? <Button size="lg" variant="secondary" disabled={pending !== null || conflict} onClick={() => setOwnEnd(item)}>{t("medical.participation.endOwn")}</Button> : null}
              <Button size="lg" variant="secondary" disabled={pending !== null || conflict} onClick={() => { setHistory(null); setTeeth(null); setOverview(item); }}>{t("medical.overview.title")}</Button>
              <Button variant="secondary" disabled={pending !== null || conflict} onClick={() => { setOverview(null); setTeeth(null); setHistory(item); }}>{t("medical.clinical.history")}</Button>
              <Button size="lg" variant="secondary" disabled={pending !== null || conflict} onClick={() => { setOverview(null); setHistory(null); setTeeth(item); }}>{t("medical.tooth.title")}</Button>
            </> : null}
            {item.state === "active" && item.member_id === access.member_id && actions?.create ? <Button size="lg" variant="secondary" disabled={pending !== null || conflict} onClick={() => setProposal(item)}>{t("medical.participation.proposals")}</Button> : null}
            {item.state === "active" && (item.member_id === access.member_id || mode === "managed") ?
              <Button size="lg" variant="secondary" disabled={pending !== null || conflict} onClick={() => setFiles({
                scope: { business_id: access.business_id, patient_id: item.patient_id,
                  ...(mode === "managed" ? { head_branch_id: item.branch_id } : { participation_id: item.id }) },
                patientName: item.patient_name, branchName: item.branch_name, returnId: String(item.id),
              })}>{t("medical.files.title")}</Button> : null}
          </div>
        </li>;
      })}
    </ul>
    <div className="flex flex-wrap gap-2">
      {cursor !== undefined ? <Button variant="secondary" disabled={pending !== null} onClick={() => setCursor(undefined)}>{t("medical.clinical.newest")}</Button> : null}
      {page?.next_before_id != null ? <Button variant="secondary" disabled={pending !== null} onClick={() => setCursor(page.next_before_id!)}>{t("medical.participation.more")}</Button> : null}
    </div>
    {overview || history || teeth ? <div ref={clinicalRef} tabIndex={-1} className="platforma-focus-ring" data-testid="participation-clinical-content">
    {overview ? <div className="space-y-3" data-testid="participation-overview">
      <p className="break-words font-semibold">{overview.patient_name} · {overview.branch_name}</p>
      <ParticipationClinicalOverview key={overview.id} businessId={access.business_id} patientId={overview.patient_id} participationId={overview.id} onDenied={onDenied}
        onHistory={() => { setHistory(overview); setOverview(null); }} />
    </div> : null}
    {history ? <ParticipationClinicalHistory key={history.id} businessId={access.business_id} patientId={history.patient_id} participationId={history.id} onDenied={onDenied} memory={historyMemory} /> : null}
    {teeth ? <div className="space-y-3" data-testid="participation-teeth">
      <p className="break-words font-semibold">{teeth.patient_name} · {teeth.branch_name}</p>
      <ParticipationToothChart key={teeth.id} businessId={access.business_id} patientId={teeth.patient_id} participationId={teeth.id} onDenied={onDenied} />
    </div> : null}
    </div> : null}
  </section>;
}

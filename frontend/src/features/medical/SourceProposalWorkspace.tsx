import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import { medicalParticipationApi as api, type Participation, type ParticipationPage, type ParticipationSource, type ProposalSourceScope } from "../../api/medicalParticipation";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { Select } from "../../components/ui/Select";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { ParticipationCommandForm } from "./ParticipationCommandForm";
import { ParticipationInvitationDetails } from "./ParticipationInvitationDetails";

type Guard = { current: { dirty: boolean; pending: boolean } };

export function SourceProposalEntry({ scope }: { scope: ProposalSourceScope }) {
  const { t } = useI18n();
  const [admitted, setAdmitted] = useState(false);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  const guard = useRef({ dirty: false, pending: false });
  const denied = useCallback((cause: unknown) => { setAdmitted(false); setError(cause); guard.current = { dirty: false, pending: false }; }, []);
  const { business_id, patient_id, source_appointment_id, source_participation_id } = scope;
  const stableScope = useMemo(() => ({ business_id, patient_id, source_appointment_id, source_participation_id }) as ProposalSourceScope,
    [business_id, patient_id, source_appointment_id, source_participation_id]);
  useEffect(() => {
    const controller = new AbortController();
    setError(null); setAdmitted(false);
    void api.proposalBranches(stableScope, controller.signal)
      .then(() => { if (!controller.signal.aborted) setAdmitted(true); })
      .catch(cause => { if (!controller.signal.aborted) setError(cause); });
    return () => controller.abort();
  }, [stableScope, attempt]);
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => { if (guard.current.dirty || guard.current.pending) { event.preventDefault(); event.returnValue = ""; } };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, []);
  const forbidden = axios.isAxiosError(error) && [401, 403].includes(error.response?.status ?? 0);
  const focusId = `proposal-entry-${business_id}-${patient_id}-${source_appointment_id ?? source_participation_id}`;
  return <>
    {admitted ? <Button id={focusId} size="lg" variant="secondary" onClick={() => setOpen(true)}>{t("medical.participation.proposals")}</Button> : null}
    {error && !forbidden && !open ? <ErrorState message={getApiErrorMessage(error)} action={<Button variant="secondary" onClick={() => setAttempt(x => x + 1)}>{t("common.retry")}</Button>} /> : null}
    <Modal open={open} title={t("medical.participation.proposals")} size="xl" closeOnBackdrop={false} focusReturnId={focusId}
      onClose={() => { if (!guard.current.pending && (!guard.current.dirty || window.confirm(t("medical.clinical.discard")))) { guard.current.dirty = false; setOpen(false); } }}>
      {error ? <ErrorState message={forbidden ? t("medical.denied") : getApiErrorMessage(error)} action={<Button variant="secondary" onClick={() => setAttempt(x => x + 1)}>{t("common.retry")}</Button>} /> :
        <SourceProposalWorkspace scope={stableScope} guard={guard} onDenied={denied} />}
    </Modal>
  </>;
}

export function SourceProposalWorkspace({ scope, guard, onDenied, onBack }: {
  scope: ProposalSourceScope; guard: Guard; onDenied: (cause: unknown) => void; onBack?: () => void;
}) {
  const { t } = useI18n();
  const [branches, setBranches] = useState<Array<{ id: number; name: string }> | null>(null);
  const [page, setPage] = useState<ParticipationPage | null>(null);
  const [cursor, setCursor] = useState<number | undefined>();
  const [branch, setBranch] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  const [pending, setPending] = useState(false);
  const [conflict, setConflict] = useState(false);
  const [formState, setFormState] = useState({ dirty: false, pending: false });
  const retry = useRef<{ fingerprint: string; key: string } | null>(null);
  const region = useRef<HTMLElement>(null);
  const focusTarget = useRef<string | null>(null);
  const { business_id, patient_id, source_appointment_id, source_participation_id } = scope;
  const stableScope = useMemo(() => ({ business_id, patient_id, source_appointment_id, source_participation_id }) as ProposalSourceScope,
    [business_id, patient_id, source_appointment_id, source_participation_id]);
  const formScope = useMemo(() => ({ businessId: business_id, patientId: patient_id, branchId: Number(branch),
    source: { source_appointment_id, source_participation_id } as ParticipationSource }), [business_id, patient_id, branch, source_appointment_id, source_participation_id]);
  useEffect(() => {
    const controller = new AbortController();
    setPage(null); setBranches(null); setError(null); setConflict(false);
    async function load() {
      const all: Array<{ id: number; name: string }> = [];
      let after: number | undefined;
      do {
        const result = await api.proposalBranches({ ...stableScope, after_branch_id: after }, controller.signal);
        all.push(...result.results);
        after = result.next_after_branch_id ?? undefined;
      } while (after !== undefined && !controller.signal.aborted);
      const result = await api.outgoing({ ...stableScope, before_id: cursor }, controller.signal);
      if (!controller.signal.aborted) { setBranches(all); setPage(result); }
    }
    void load().catch(cause => {
      if (controller.signal.aborted) return;
      if (axios.isAxiosError(cause) && [401, 403].includes(cause.response?.status ?? 0)) onDenied(cause);
      else setError(cause);
    });
    return () => controller.abort();
  }, [stableScope, cursor, attempt, onDenied]);
  useLayoutEffect(() => {
    if (!creating && page && focusTarget.current) {
      const target = region.current?.querySelector<HTMLElement>(`[data-proposal-focus="${focusTarget.current}"]`);
      if (target) { target.focus(); focusTarget.current = null; }
    }
  }, [creating, page]);
  function refresh() {
    guard.current.dirty = false; setFormState({ dirty: false, pending: false });
    setCreating(false); setBranch(""); setPage(null); setBranches(null); setAttempt(x => x + 1);
  }
  async function withdraw(item: Participation) {
    if (guard.current.pending || conflict) return;
    guard.current.pending = true; setPending(true); setError(null);
    const payload = { business_id, patient_id, expected_revision: item.revision };
    const fingerprint = JSON.stringify({ id: item.id, ...payload });
    if (retry.current?.fingerprint !== fingerprint) retry.current = { fingerprint, key: crypto.randomUUID() };
    try {
      await api.withdraw(item.id, payload, retry.current.key);
      focusTarget.current = String(item.id); refresh();
    } catch (cause) {
      if (axios.isAxiosError(cause) && [401, 403].includes(cause.response?.status ?? 0)) onDenied(cause);
      else { setError(cause); if (axios.isAxiosError(cause) && cause.response?.status === 409) setConflict(true); }
    } finally { guard.current.pending = false; setPending(false); }
  }
  return <section className="space-y-4" ref={region} data-testid="source-proposal-workspace">
    {creating ? <>
      <Select label={t("medical.branch")} value={branch} disabled={formState.pending} options={[
        { value: "", label: t("medical.selectBranch") }, ...(branches ?? []).map(row => ({ value: row.id, label: row.name }))]}
        onChange={event => { if (!guard.current.pending && (!guard.current.dirty || window.confirm(t("medical.clinical.discard")))) setBranch(event.target.value); }} />
      {branch ? <ParticipationCommandForm key={branch} scope={formScope} guard={guard} onStateChange={setFormState} onDenied={onDenied}
        onSaved={() => { focusTarget.current = "new"; refresh(); }} /> : null}
      <Button variant="secondary" disabled={formState.pending} onClick={() => {
        if (!guard.current.pending && (!guard.current.dirty || window.confirm(t("medical.clinical.discard")))) { focusTarget.current = "new"; refresh(); }
      }}>{t("common.cancel")}</Button>
    </> : <>
      <div className="flex flex-wrap gap-2">
        {branches?.length ? <Button size="lg" data-proposal-focus="new" disabled={pending || conflict} onClick={() => setCreating(true)}>{t("medical.participation.invite")}</Button> : null}
        <Button variant="secondary" disabled={pending} onClick={refresh}>{t("medical.clinical.reload")}</Button>
      </div>
      {!page && !error ? <LoadingState /> : null}
      {error ? <ErrorState message={conflict ? t("medical.clinical.conflict") : getApiErrorMessage(error)} /> : null}
      {page && !page.results.length ? <p className="text-sm text-platforma-subtle">{t("medical.participation.noOutgoing")}</p> : null}
      <ul className="divide-y divide-platforma-border">{page?.results.map(item => <li key={item.id} tabIndex={-1} data-proposal-focus={item.id}
        data-testid={`outgoing-${item.id}`} className="space-y-3 py-4">
        <p className="break-words font-semibold">{item.member_name} · {item.branch_name}</p>
        <p className="text-sm text-platforma-subtle">{t(`medical.participation.state.${item.state}`)}</p>
        <ParticipationInvitationDetails item={item} />
        {item.decline_reason ? <p className="break-words whitespace-pre-wrap text-sm">{t("medical.participation.declineReason")}: {item.decline_reason}</p> : null}
        {item.state === "pending" ? <Button size="lg" variant="secondary" disabled={pending || conflict} onClick={() => void withdraw(item)}>{t("medical.participation.withdraw")}</Button> : null}
      </li>)}</ul>
      <div className="flex flex-wrap gap-2">
        {cursor !== undefined ? <Button variant="secondary" disabled={pending} onClick={() => setCursor(undefined)}>{t("medical.clinical.newest")}</Button> : null}
        {page?.next_before_id != null ? <Button variant="secondary" disabled={pending} onClick={() => setCursor(page.next_before_id!)}>{t("medical.participation.more")}</Button> : null}
      </div>
    </>}
    {onBack ? <Button variant="secondary" disabled={pending || formState.pending} onClick={() => {
      if (!guard.current.pending && (!guard.current.dirty || window.confirm(t("medical.clinical.discard")))) { guard.current.dirty = false; onBack(); }
    }}>{t("common.back")}</Button> : null}
  </section>;
}

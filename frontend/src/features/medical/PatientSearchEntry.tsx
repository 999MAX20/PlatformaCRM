import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import { useNavigate } from "react-router";
import { medicalPatientsApi, type PatientScope, type PatientSearchKind, type PatientSearchPage, type PatientSearchRequest } from "../../api/medicalPatients";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { Modal } from "../../components/ui/Modal";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { PatientRegistrationForm } from "./PatientRegistrationForm";
import type { RoleDraftState } from "./roles/MedicalRoleCommand";

export function PatientSearchEntry({ businessId, userId }: { businessId: number; userId: number }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [branch, setBranch] = useState("");
  const [creating, setCreating] = useState(false);
  const creationGuard = useRef<RoleDraftState>({ dirty: false, pending: false });
  function canLeaveCreation() { return !creationGuard.current.pending && (!creationGuard.current.dirty || window.confirm(t("medical.clinical.discard"))); }
  const access = useQuery({ queryKey: ["medical-patient-search-access", businessId, userId],
    queryFn: ({ signal }) => medicalPatientsApi.searchAccess(businessId, signal), retry: false });
  const branches = access.data?.branches ?? [];
  const selected = branch || (branches.length === 1 ? String(branches[0].id) : "");
  const valid = branches.some(item => String(item.id) === selected);
  if (axios.isAxiosError(access.error) && access.error.response?.status === 403) return null;
  if (access.error) return <ErrorState message={getApiErrorMessage(access.error)} action={<Button variant="secondary" onClick={() => void access.refetch()}>{t("common.retry")}</Button>} />;
  if (!branches.length) return null;
  return <div className="flex justify-end">
    <Button variant="secondary" size="lg" data-testid="patient-search-open" data-focus-return-id="patient-search-open" onClick={() => setOpen(true)}>{t("medical.search.title")}</Button>
    <Modal title={t(creating ? "medical.registration.title" : "medical.search.title")} open={open} onClose={() => { if (canLeaveCreation()) { setOpen(false); setCreating(false); } }} size="lg" testId="patient-search" focusReturnId="patient-search-open">
      {open ? <div className="space-y-4">
        <Select label={t("medical.branch")} value={selected} onChange={event => { if (canLeaveCreation()) { setBranch(event.target.value); setCreating(false); } }} options={[
          { value: "", label: t("medical.selectBranch") }, ...branches.map(item => ({ value: item.id, label: item.name })),
        ]} />
        {valid ? <PatientSearchForm key={`${businessId}:${userId}:${selected}`} scope={{ business_id: businessId, branch_id: Number(selected) }}
          canCreate={access.data?.actions.create === true} creating={creating} onCreatingChange={setCreating} creationGuard={creationGuard} /> : null}
      </div> : null}
    </Modal>
  </div>;
}

function PatientSearchForm({ scope, canCreate, creating, onCreatingChange, creationGuard }: { scope: PatientScope; canCreate: boolean; creating: boolean;
  onCreatingChange: (value: boolean) => void; creationGuard: { current: RoleDraftState } }) {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [kind, setKind] = useState<PatientSearchKind>("name");
  const [query, setQuery] = useState("");
  const [archived, setArchived] = useState(false);
  const [page, setPage] = useState<PatientSearchPage | null>(null);
  const [submitted, setSubmitted] = useState<PatientSearchRequest | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const [denied, setDenied] = useState(false);
  const request = useRef<AbortController | null>(null);
  useEffect(() => () => request.current?.abort(), []);
  function clearResults() {
    request.current?.abort(); setLoading(false); setPage(null); setSubmitted(null); setError(null);
  }
  async function search(offset = 0) {
    request.current?.abort();
    const controller = new AbortController(); request.current = controller;
    const payload: PatientSearchRequest = offset && submitted ? { ...submitted, offset } : {
      ...scope, kind, query: query.trim(), include_archived: archived, offset: 0, limit: 25,
    };
    setLoading(true); setError(null);
    if (!offset) setPage(null);
    try {
      const result = await medicalPatientsApi.resolve(payload, controller.signal);
      if (controller.signal.aborted) return;
      setSubmitted(payload);
      setPage(previous => ({ ...result, results: offset ? [...(previous?.results ?? []), ...result.results] : result.results }));
    } catch (cause) {
      if (controller.signal.aborted) return;
      if (axios.isAxiosError(cause) && [401, 403].includes(cause.response?.status ?? 0)) {
        setDenied(true); setQuery(""); setPage(null); setSubmitted(null);
      } else setError(cause);
    } finally { if (!controller.signal.aborted) setLoading(false); }
  }
  if (denied) return <ErrorState message={t("medical.denied")} />;
  if (creating) return <PatientRegistrationForm scope={scope} initialKind={kind} initialQuery={query} hasMatches={!!page?.results.length}
    guard={creationGuard} onCancel={() => onCreatingChange(false)} onSaved={clientId => void navigate(`/app/clients/${clientId}`)}
    onDenied={() => { setQuery(""); setPage(null); setSubmitted(null); setDenied(true); }} />;
  return <div className="space-y-4">
    <form className="space-y-4" onSubmit={event => { event.preventDefault(); void search(); }}>
      <Select label={t("medical.search.field")} value={kind} onChange={event => { clearResults(); setKind(event.target.value as PatientSearchKind); setQuery(""); }} options={
        (["name", "phone", "email", "birth", "iin"] as const).map(value => ({ value, label: t(`medical.search.${value}`) }))} />
      <Input label={t(`medical.search.${kind}`)} value={query} onChange={event => { clearResults(); setQuery(event.target.value); }}
        type={kind === "birth" ? "date" : "text"} inputMode={kind === "iin" || kind === "phone" ? "tel" : kind === "email" ? "email" : "text"}
        autoComplete="off" maxLength={kind === "iin" ? 12 : 255} minLength={kind === "phone" ? 4 : 2} required data-testid="patient-search-query" />
      <label className="flex min-h-11 cursor-pointer items-center gap-3 text-sm text-platforma-text">
        <input className="platforma-focus-ring h-5 w-5 shrink-0 accent-brand-600" type="checkbox" checked={archived} onChange={event => { clearResults(); setArchived(event.target.checked); }} />
        {t("medical.search.archived")}
      </label>
      <Button type="submit" size="lg" disabled={loading || query.trim().length < 2}>{t("common.search")}</Button>
    </form>
    {error ? <ErrorState message={getApiErrorMessage(error)} action={<Button variant="secondary" onClick={() => void search(page?.next_offset ?? 0)}>{t("common.retry")}</Button>} /> : null}
    {loading ? <LoadingState /> : null}
    {page ? <div aria-live="polite" aria-busy={loading} data-testid="patient-search-results">
      {!page.results.length ? <p className="text-sm text-platforma-subtle">{t("medical.search.empty")}</p> : <ul className="divide-y divide-platforma-border">
        {page.results.map(item => <li key={item.client_id} className="flex flex-col gap-3 py-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 space-y-1 break-words text-sm text-platforma-subtle">
            <p className="font-semibold text-platforma-text">{item.full_name}</p>
            <p>{t(`medical.search.${item.match}`)}</p>
            {item.phone ? <p>{item.phone}</p> : null}{item.email ? <p>{item.email}</p> : null}
            {item.date_of_birth ? <p>{t("medical.birth")}: {item.date_of_birth}</p> : null}
            {item.identity_status ? <p>{t(`medical.${item.identity_status}`)}</p> : null}
            {item.is_archived ? <p>{t("clients.card.archived")}</p> : null}
          </div>
          <Button variant="secondary" size="lg" className="shrink-0" onClick={() => void navigate(`/app/clients/${item.client_id}`)} aria-label={`${t("common.open")}: ${item.full_name}`}>{t("common.open")}</Button>
        </li>)}
      </ul>}
      {page.next_offset !== null ? <Button variant="secondary" size="lg" disabled={loading} onClick={() => void search(page.next_offset!)}>{t("medical.search.more")}</Button> : null}
      {canCreate && !page.results.some(item => item.match === "exact_confirmed") ? <div className="mt-4">
        <Button variant="secondary" size="lg" disabled={loading} onClick={() => onCreatingChange(true)}>{t("medical.registration.create")}</Button>
      </div> : null}
    </div> : null}
  </div>;
}

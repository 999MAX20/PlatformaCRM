import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { medicalReceptionAdministrationApi as api, type AdministrativeScope, type AdministrativeOption } from "../../api/medicalReceptionAdministration";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { Textarea } from "../../components/ui/Textarea";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { useUnsavedEntryWarning } from "../auth/useUnsavedEntryWarning";
import { MedicalRoleCommand, type RoleDraftState, type RoleFormControl } from "./roles/MedicalRoleCommand";
import { medicalRoleDenied } from "./roles/useMedicalRolePage";

export function AdministrativeFollowUp({ scope }: { scope: AdministrativeScope }) {
  const { t } = useI18n(); const navigate = useNavigate();
  const [allowed, setAllowed] = useState(false); const [open, setOpen] = useState(false);
  const [attempt, setAttempt] = useState(0); const [error, setError] = useState<unknown>(null);
  const [result, setResult] = useState<number | null>(null);
  const [draft, setDraft] = useState<RoleDraftState>({ dirty: false, pending: false });
  const guard = useRef(draft);
  const denied = useCallback((cause: unknown) => { setAllowed(false); setOpen(false); setResult(null); setError(cause); setDraft({ dirty: false, pending: false }); }, []);
  useUnsavedEntryWarning(draft.dirty || draft.pending);
  useEffect(() => {
    const active = new AbortController(); setAllowed(false); setError(null);
    void api.options({ ...scope, kind: "appointments" }, active.signal).then(() => { if (!active.signal.aborted) setAllowed(true); })
      .catch(cause => { if (!active.signal.aborted && !medicalRoleDenied(cause)) setError(cause); });
    return () => active.abort();
  }, [scope.business_id, scope.branch_id, scope.client_id, attempt]);
  function close() { if (!guard.current.pending && (!guard.current.dirty || window.confirm(t("medical.clinical.discard")))) setOpen(false); }
  return <div className="space-y-3" data-testid="administrative-follow-up">
    {error ? <ErrorState message={getApiErrorMessage(error)} action={<Button variant="secondary" onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button>} /> : null}
    {allowed ? <Button size="lg" variant="secondary" id="medical-administrative-follow-up" onClick={() => setOpen(true)}>{t("medical.reception.administrative")}</Button> : null}
    {result ? <Button size="lg" variant="secondary" onClick={() => navigate(`/app/medical/reception?branch=${scope.branch_id}&request=${result}`)}>{t("medical.reception.queue")}</Button> : null}
    <Modal open={open} onClose={close} closeOnBackdrop={false} size="lg" title={t("medical.reception.administrative")} focusReturnId="medical-administrative-follow-up"
      className="[&>header]:h-auto [&>header]:min-h-16 [&>header]:py-3 [&>header>h2]:whitespace-normal [&>header>h2]:break-words">
      {open ? <AdministrativeForm scope={scope} onResult={setResult} control={{ guard, onDraft: setDraft, onSaved: () => setOpen(false), onDenied: denied }} /> : null}
    </Modal>
  </div>;
}

function AdministrativeForm({ scope, control, onResult }: { scope: AdministrativeScope; control: RoleFormControl; onResult: (id: number) => void }) {
  const { t } = useI18n();
  const [source, setSource] = useState<AdministrativeOption | null>(null); const [service, setService] = useState<AdministrativeOption | null>(null);
  const [staff, setStaff] = useState<AdministrativeOption | null>(null); const [from, setFrom] = useState(""); const [until, setUntil] = useState("");
  const [onsite, setOnsite] = useState(true); const [reason, setReason] = useState("");
  const payload = source?.updated_at && service && staff && from && until >= from && reason.trim() ? { ...scope,
    source_appointment_id: source.id, expected_updated_at: source.updated_at, service_id: service.id, preferred_resource_id: staff.id,
    recommended_from: from, recommended_until: until, patient_in_clinic: onsite, reason } : null;
  return <MedicalRoleCommand payload={payload} dirty={Boolean(source || service || staff || from || until || reason || !onsite)} label={t("medical.reception.administrativeSave")}
    submit={async (value, key) => { const result = await api.create(value, key); onResult(result.id); }} control={control}>
    <p className="text-sm text-platforma-subtle">{t("medical.reception.administrativeHint")}</p>
    <AdministrativeChoice scope={scope} kind="appointments" value={source} onChange={setSource} label={t("medical.reception.sourceAppointment")} onDenied={control.onDenied} />
    <AdministrativeChoice scope={scope} kind="services" value={service} onChange={setService} label={t("medical.reception.service")} onDenied={control.onDenied} />
    <AdministrativeChoice scope={scope} kind="staff" value={staff} onChange={setStaff} label={t("medical.reception.staff")} onDenied={control.onDenied} />
    <div className="grid min-w-0 gap-4 sm:grid-cols-2">
      <Input type="date" label={t("medical.reception.from")} value={from} required onChange={event => setFrom(event.target.value)} />
      <Input type="date" label={t("medical.reception.until")} value={until} min={from} required onChange={event => setUntil(event.target.value)} />
    </div>
    <label className="flex min-h-11 items-center gap-2"><input type="checkbox" className="h-5 w-5 accent-brand-500" checked={onsite} onChange={event => setOnsite(event.target.checked)} />{t("medical.reception.onsite")}</label>
    <Textarea label={t("medical.reception.contactReason")} value={reason} required maxLength={1000} onChange={event => setReason(event.target.value)} />
  </MedicalRoleCommand>;
}

function AdministrativeChoice({ scope, kind, value, onChange, label, onDenied }: { scope: AdministrativeScope; kind: string;
  value: AdministrativeOption | null; onChange: (option: AdministrativeOption | null) => void; label: string; onDenied: (cause: unknown) => void }) {
  const { t, language } = useI18n();
  const [rows, setRows] = useState<AdministrativeOption[]>([]); const [next, setNext] = useState<number | null>(null);
  const [error, setError] = useState<unknown>(null); const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState(""); const active = useRef<AbortController | null>(null);
  async function load(after_id = 0) {
    active.current?.abort(); const controller = new AbortController(); active.current = controller;
    setLoading(true); setError(null);
    try { const page = await api.options({ ...scope, kind, search, after_id }, controller.signal);
      if (!controller.signal.aborted) { setRows(old => after_id ? [...old, ...page.results] : page.results); setNext(page.next_id); }
    } catch (cause) { if (!controller.signal.aborted) { if (medicalRoleDenied(cause)) onDenied(cause); else setError(cause); } }
    finally { if (!controller.signal.aborted) setLoading(false); }
  }
  useEffect(() => { void load(); return () => active.current?.abort(); }, [scope.business_id, scope.branch_id, scope.client_id, kind]);
  const options = value && !rows.some(row => row.id === value.id) ? [value, ...rows] : rows;
  return <div className="min-w-0 space-y-2">
    {kind !== "appointments" ? <div className="flex min-w-0 items-end gap-2"><div className="min-w-0 flex-1"><Input label={`${t("common.search")}: ${label}`} value={search} maxLength={100} onChange={event => setSearch(event.target.value)} /></div><Button type="button" variant="secondary" disabled={loading} onClick={() => void load()}>{t("common.search")}</Button></div> : null}
    <Select label={label} value={value?.id ?? ""} disabled={loading} options={[{ value: "", label: t("medical.reception.chooseOption") }, ...options.map(row => ({ value: row.id, label: row.start_at ? `${new Date(row.start_at).toLocaleString(language)} · ${row.name} · ${row.service_name}` : row.name }))]}
      onChange={event => onChange(options.find(row => row.id === Number(event.target.value)) ?? null)} />
    {loading ? <LoadingState /> : null}
    {error ? <ErrorState message={getApiErrorMessage(error)} action={<Button type="button" variant="secondary" onClick={() => void load()}>{t("common.retry")}</Button>} /> : null}
    {next !== null ? <Button type="button" variant="secondary" disabled={loading} onClick={() => void load(next)}>{t("medical.templates.more")}</Button> : null}
  </div>;
}

import { useEffect, useRef, useState } from "react";
import { medicalReceptionDutyApi as api, type DutyOptions } from "../../api/medicalReceptionDuty";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { Textarea } from "../../components/ui/Textarea";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { MedicalRoleCommand, type RoleFormControl } from "./roles/MedicalRoleCommand";
import { medicalRoleDenied } from "./roles/useMedicalRolePage";

const localTime = (value: string) => { const date = new Date(value); return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16); };
export function ReceptionDutyForm({ businessId, control }: { businessId: number; control: RoleFormControl }) {
  const { t } = useI18n();
  const [branches, setBranches] = useState<DutyOptions>({ results: [], next_id: null });
  const [members, setMembers] = useState<DutyOptions>({ results: [], next_id: null });
  const [branch, setBranch] = useState("");
  const [lead, setLead] = useState(""); const [deputy, setDeputy] = useState("");
  const [available, setAvailable] = useState(true);
  const [start, setStart] = useState(""); const [end, setEnd] = useState("");
  const [reason, setReason] = useState(""); const [dirty, setDirty] = useState(false);
  const [loading, setLoading] = useState(false); const [error, setError] = useState<unknown>(null);
  const controller = useRef<AbortController | null>(null);
  const onDenied = control.onDenied;
  async function load(kind: "branches" | "members", after_id = 0) {
    controller.current?.abort(); const active = new AbortController(); controller.current = active;
    setLoading(true); setError(null);
    try {
      const page = await api.read({ business_id: businessId, kind, after_id, ...(kind === "members" ? { branch_id: Number(branch) } : {}) }, active.signal);
      if (active.signal.aborted) return;
      if (kind === "branches") setBranches(previous => ({ ...page, results: after_id ? [...previous.results, ...page.results] : page.results }));
      else {
        setMembers(previous => ({ ...page, results: after_id ? [...previous.results, ...page.results] : page.results }));
        if (!after_id) {
          setLead(page.duty ? String(page.duty.lead_id) : ""); setDeputy(page.duty?.deputy_id ? String(page.duty.deputy_id) : "");
          setAvailable(page.duty?.lead_available ?? true);
          setStart(page.duty ? localTime(page.duty.starts_at) : ""); setEnd(page.duty ? localTime(page.duty.ends_at) : "");
        }
      }
    } catch (cause) { if (!active.signal.aborted) { if (medicalRoleDenied(cause)) onDenied(cause); else setError(cause); } }
    finally { if (!active.signal.aborted) setLoading(false); }
  }
  useEffect(() => { void load(branch ? "members" : "branches"); return () => controller.current?.abort(); }, [businessId, branch]);
  const changed = () => setDirty(true);
  const ready = !loading && !error && branch && lead && start && end && new Date(end) > new Date(start) && reason.trim();
  const payload = ready ? { business_id: businessId, branch_id: Number(branch), lead_id: Number(lead), deputy_id: deputy ? Number(deputy) : null,
    lead_available: available, starts_at: new Date(start).toISOString(), ends_at: new Date(end).toISOString(), expected_revision: members.duty?.revision ?? 0, reason } : null;
  return <div data-testid="reception-duty"><MedicalRoleCommand payload={payload} dirty={dirty} submit={api.save} label={t("medical.reception.dutySave")} control={control}>
    <Select label={t("medical.branch")} value={branch} disabled={dirty || loading} options={[{ value: "", label: t("medical.selectBranch") }, ...branches.results.map(row => ({ value: row.id, label: row.name }))]}
      onChange={event => setBranch(event.target.value)} />
    {branches.next_id !== null && !branch ? <Button type="button" variant="secondary" disabled={loading} onClick={() => void load("branches", branches.next_id!)}>{t("medical.templates.more")}</Button> : null}
    {loading ? <LoadingState /> : null}
    {error ? <ErrorState message={getApiErrorMessage(error)} action={<Button type="button" variant="secondary" onClick={() => void load(branch ? "members" : "branches")}>{t("common.retry")}</Button>} /> : null}
    {branch && !loading ? <>
      <Select label={t("medical.reception.dutyLead")} value={lead} options={[{ value: "", label: t("medical.reception.recipient") }, ...members.results.map(row => ({ value: row.id, label: row.name }))]} onChange={event => { setLead(event.target.value); changed(); }} />
      <Select label={t("medical.reception.dutyDeputy")} value={deputy} options={[{ value: "", label: t("medical.reception.noDeputy") }, ...members.results.map(row => ({ value: row.id, label: row.name }))]} onChange={event => { setDeputy(event.target.value); changed(); }} />
      {members.next_id !== null ? <Button type="button" variant="secondary" onClick={() => void load("members", members.next_id!)}>{t("medical.templates.more")}</Button> : null}
      <label className="flex min-h-11 items-center gap-2"><input type="checkbox" className="h-5 w-5 accent-brand-500" checked={available} onChange={event => { setAvailable(event.target.checked); changed(); }} />{t("medical.reception.leadAvailable")}</label>
      <p className="text-sm text-platforma-subtle">{t("medical.reception.dutyTimezone", { zone: Intl.DateTimeFormat().resolvedOptions().timeZone })}</p>
      <div className="grid min-w-0 gap-4 sm:grid-cols-2">
        <Input type="datetime-local" label={t("medical.reception.dutyStart")} value={start} required onChange={event => { setStart(event.target.value); changed(); }} />
        <Input type="datetime-local" label={t("medical.reception.dutyEnd")} value={end} required onChange={event => { setEnd(event.target.value); changed(); }} />
      </div>
      <Textarea label={t("medical.reception.contactReason")} value={reason} required maxLength={1000} onChange={event => { setReason(event.target.value); changed(); }} />
    </> : null}
  </MedicalRoleCommand></div>;
}

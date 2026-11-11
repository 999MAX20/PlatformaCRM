import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { specialistLifecycleApi, type Absence } from "../../api/branches";
import type { ManagementResource } from "../../api/management";
import { useActionConfirm } from "../../components/actions/ActionConfirmProvider";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { FormShell, managementQueryKeys } from "./FormShell";

export function AbsenceDialog({ item, onClose }: { item: ManagementResource; onClose: () => void }) {
  const { t } = useI18n();
  const cache = useQueryClient();
  const confirm = useActionConfirm();
  const query = useQuery({ queryKey: ["specialist-absences", item.id], queryFn: () => specialistLifecycleApi.absences(item.id) });
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [reason, setReason] = useState<Absence["reason"]>("unavailable");
  const [editing, setEditing] = useState<Absence | null>(null);
  const [reasonDirty, setReasonDirty] = useState(false);
  const removal = useMutation({ mutationFn: (id: number) => specialistLifecycleApi.removeAbsence(item.id, id), onSuccess: async () => {
    await Promise.all([...managementQueryKeys, "specialist-absences"].map(key => cache.invalidateQueries({ queryKey: [key] })));
  } });
  return <FormShell dirty={reasonDirty} title={`${t("management.unavailability")}: ${item.name}`} onClose={onClose} save={async () => {
    await specialistLifecycleApi.addAbsence(item.id, { id: editing?.id, starts_on: start, ends_on: end, reason, branch: editing ? editing.branch : item.resource_type === "staff" ? null : item.branch });
    await cache.invalidateQueries({ queryKey: ["specialist-absences", item.id] });
  }}>
    {query.isPending ? <LoadingState /> : query.error ? <ErrorState error={query.error} action={<Button type="button" onClick={() => void query.refetch()}>{t("common.retry")}</Button>} /> : <div className="space-y-2">
      {!query.data?.length && <p className="text-sm text-platforma-subtle">{t("branches.noAbsences")}</p>}
      {query.data?.map(row => <div key={row.id} className="flex flex-wrap items-center justify-between gap-2 border-b border-platforma-border py-2 text-sm">
        <span>{row.starts_on} – {row.ends_on} · {t(`branches.${row.reason}`)}</span>
        <Button type="button" variant="secondary" onClick={() => { setEditing(row); setStart(row.starts_on); setEnd(row.ends_on); setReason(row.reason); }}>{t("common.edit")}</Button>
        <Button type="button" variant="secondary" disabled={removal.isPending} onClick={async () => {
          if ((await confirm({ title: t("branches.removeAbsence"), confirmLabel: t("branches.removeAbsence"), tone: "warning" })).confirmed) removal.mutate(row.id);
        }}>{t("branches.removeAbsence")}</Button>
      </div>)}
    </div>}
    {removal.error && <ErrorState error={removal.error} />}
    <div className="grid min-w-0 gap-4 sm:grid-cols-2">
      <Input label={t("branches.absenceStart")} type="date" required value={start} onChange={event => setStart(event.target.value)} />
      <Input label={t("branches.absenceEnd")} type="date" required min={start} value={end} onChange={event => setEnd(event.target.value)} />
    </div>
    <Select label={t("branches.reason")} value={reason} onChange={event => { setReasonDirty(true); setReason(event.target.value as Absence["reason"]); }} options={(item.resource_type === "staff" ? ["unavailable", "vacation", "sick"] : ["unavailable"]).map(value => ({ value, label: t(`branches.${value}`) }))} />
  </FormShell>;
}

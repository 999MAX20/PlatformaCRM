import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";
import { branchesApi, specialistLifecycleApi, type Absence } from "../../../api/branches";
import { useActionConfirm } from "../../../components/actions/ActionConfirmProvider";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { todayInTimeZone } from "../../../lib/format";
import { useI18n } from "../../../lib/i18n";
import { useActiveBusiness } from "../../../hooks/useBusiness";
import type { Resource } from "../../../types";

export function SpecialistLifecycle({ resource, canManage }: { resource: Resource; canManage: boolean }) {
  const { t } = useI18n();
  const { business } = useActiveBusiness();
  const cache = useQueryClient();
  const confirm = useActionConfirm();
  const [start, setStart] = useState(todayInTimeZone(business?.timezone || "Asia/Almaty"));
  const [end, setEnd] = useState(start);
  const [reason, setReason] = useState<Absence["reason"]>("unavailable");
  const [branch, setBranch] = useState("");
  const [review, setReview] = useState(false);
  const [disableAccess, setDisableAccess] = useState(false);
  const branches = useQuery({ queryKey: ["branches", resource.business], queryFn: () => branchesApi.listAll({ business: resource.business }) });
  const absences = useQuery({ queryKey: ["specialist-absences", resource.id], queryFn: () => specialistLifecycleApi.absences(resource.id) });
  const preview = useQuery({ queryKey: ["specialist-retirement", resource.id], queryFn: () => specialistLifecycleApi.preview(resource.id), enabled: review });
  const mutation = useMutation({ mutationFn: (operation: () => Promise<unknown>) => operation(), onSuccess: async () => {
    await Promise.all([cache.invalidateQueries({ queryKey: ["resources"] }), cache.invalidateQueries({ queryKey: ["specialist-absences", resource.id] }), cache.invalidateQueries({ queryKey: ["specialist-retirement", resource.id] }), cache.invalidateQueries({ queryKey: ["available-slots"] }), cache.invalidateQueries({ queryKey: ["branch-catalog"] })]);
  } });
  const pendingLabels: Record<string, string> = { appointments: "pendingAppointments", tasks: "pendingTasks", leads: "pendingLeads", deals: "pendingDeals", conversations: "pendingConversations" };
  const pendingLinks: Record<string, string> = { appointments: `/app/calendar?resource=${resource.id}`, tasks: `/app/tasks?assignee=${resource.linked_user || ""}`, leads: "/app/leads", deals: `/app/deals?owner=${resource.linked_user || ""}`, conversations: "/app/inbox" };
  if (resource.retired_at) return <p className="text-sm text-platforma-subtle">{t("branches.retired")}</p>;
  return <section className="space-y-4 rounded-card border border-platforma-border bg-surface-card p-4">
    <h3 className="text-sm font-semibold">{t("branches.absences")}</h3>
    {mutation.error && <ErrorState error={mutation.error} />}
    {absences.isLoading ? <LoadingState /> : absences.error ? <ErrorState error={absences.error} /> : <div className="space-y-2">
      {!absences.data?.length && <p className="text-sm text-platforma-subtle">{t("branches.noAbsences")}</p>}
      {absences.data?.map((absence) => <div key={absence.id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
        <span>{absence.starts_on} — {absence.ends_on} · {t(`branches.${absence.reason}`)}</span>
        <Link className="platforma-focus-ring text-brand-700 underline" to={`/app/calendar?resource=${resource.id}&date=${absence.starts_on}${absence.branch ? `&branch=${absence.branch}` : ""}`}>{t("branches.pendingAppointments")}</Link>
        {canManage && <Button variant="secondary" disabled={mutation.isPending} onClick={() => mutation.mutate(() => specialistLifecycleApi.removeAbsence(resource.id, absence.id))}>{t("branches.removeAbsence")}</Button>}
      </div>)}
    </div>}
    {canManage && <form className="space-y-3" onSubmit={(event) => { event.preventDefault(); mutation.mutate(() => specialistLifecycleApi.addAbsence(resource.id, { starts_on: start, ends_on: end, reason, branch: branch ? Number(branch) : null })); }}>
      <div className="grid gap-3 sm:grid-cols-2"><Input label={t("branches.absenceStart")} type="date" required value={start} onChange={(event) => setStart(event.target.value)} /><Input label={t("branches.absenceEnd")} type="date" required min={start} value={end} onChange={(event) => setEnd(event.target.value)} /></div>
      <Select label={t("branches.reason")} value={reason} onChange={(event) => setReason(event.target.value as Absence["reason"])} options={["unavailable", "vacation", "sick"].map((value) => ({ value, label: t(`branches.${value}`) }))} />
      {!!branches.data?.length && <Select label={t("branches.branch")} value={branch} onChange={(event) => setBranch(event.target.value)} options={[{ value: "", label: t("branches.all") }, ...branches.data.filter((item) => item.can_manage).map((item) => ({ value: item.id, label: item.name }))]} />}
      <Button type="submit" isLoading={mutation.isPending}>{t("branches.addAbsence")}</Button>
    </form>}
    {canManage && <Button variant="secondary" onClick={() => setReview(!review)}>{t("branches.retire")}</Button>}
    {review && <div className="space-y-3 border-t border-platforma-border pt-3">
      {preview.isLoading ? <LoadingState /> : preview.error ? <ErrorState error={preview.error} /> : preview.data && <>
        <h4 className="text-sm font-semibold">{t("branches.pendingWork")}</h4>
        <div className="grid gap-2">{Object.entries(preview.data.pending).map(([key, count]) => <Link key={key} className="text-sm text-brand-700 underline" to={pendingLinks[key]}>{t(`branches.${pendingLabels[key]}`)}: {count}</Link>)}</div>
        {!!resource.linked_user && <label className="flex min-h-10 items-center gap-2 text-sm"><input type="checkbox" checked={disableAccess} onChange={(event) => setDisableAccess(event.target.checked)} />{t("branches.disableAccess")}</label>}
        <Button variant="warning" disabled={mutation.isPending || Object.values(preview.data.pending).some(Boolean)} onClick={async () => {
          const result = await confirm({ title: t("branches.retire"), description: t("branches.retireConfirm"), tone: "warning" });
          if (result.confirmed) mutation.mutate(() => specialistLifecycleApi.retire(resource.id, disableAccess));
        }}>{t("branches.retire")}</Button>
      </>}
    </div>}
  </section>;
}

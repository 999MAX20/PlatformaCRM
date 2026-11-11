import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router";
import { branchesApi, type Branch, type BranchCatalog } from "../../../api/branches";
import { useActionConfirm } from "../../../components/actions/ActionConfirmProvider";
import { Button } from "../../../components/ui/Button";
import { Select } from "../../../components/ui/Select";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import type { Resource } from "../../../types";

export function StaffAssignments({ resource, branches, onDirtyChange }: { resource: Resource; branches: Branch[]; onDirtyChange: (dirty: boolean) => void }) {
  const { t } = useI18n();
  const confirm = useActionConfirm();
  const [params] = useSearchParams();
  const [selected, setSelected] = useState(params.get("branch") || "");
  const [dirty, setDirty] = useState(false);
  const available = branches.filter(branch => branch.can_work || branch.can_manage);
  const branch = available.find(item => String(item.id) === selected) || available[0];
  const query = useQuery({ queryKey: [branch?.can_manage ? "branch-configuration" : "branch-catalog", branch?.id], queryFn: () => branch!.can_manage ? branchesApi.configuration(branch!.id) : branchesApi.catalog(branch!.id), enabled: !!branch });
  useEffect(() => { onDirtyChange(dirty); return () => onDirtyChange(false); }, [dirty, onDirtyChange]);
  return <section className="space-y-3 border-t border-platforma-border pt-4">
    <h3 className="text-sm font-semibold">{t("business.assignments")}</h3>
    <Select label={t("branches.branch")} value={branch?.id || ""} options={available.map(item => ({ value: item.id, label: item.name }))}
      onChange={async event => {
        const next = event.target.value;
        if (dirty && !(await confirm({ title: t("workingHours.discardChanges"), confirmLabel: t("actions.discardChanges"), tone: "warning" })).confirmed) return;
        setDirty(false); setSelected(next);
      }} />
    {query.isLoading ? <LoadingState /> : query.error ? <ErrorState error={query.error} action={<Button onClick={() => void query.refetch()}>{t("common.retry")}</Button>} /> : branch && query.data ?
      branch.uses_business_defaults ? <p className="text-sm text-platforma-subtle">{t("business.automaticAssignment")}</p> :
        <AssignmentForm key={`${branch.id}:${resource.id}`} branch={branch} resource={resource} catalog={query.data} onDirtyChange={setDirty} /> : null}
  </section>;
}

function AssignmentForm({ branch, resource, catalog, onDirtyChange }: { branch: Branch; resource: Resource; catalog: BranchCatalog; onDirtyChange: (dirty: boolean) => void }) {
  const { t } = useI18n();
  const cache = useQueryClient();
  const existing = catalog.assignments.find(item => item.resource === resource.id);
  const [active, setActive] = useState(existing?.is_active ?? false);
  const [services, setServices] = useState(existing?.service_ids || []);
  const [saved, setSaved] = useState(JSON.stringify([active, [...services].sort()]));
  const dirty = saved !== JSON.stringify([active, [...services].sort()]);
  const mutation = useMutation({ mutationFn: () => branchesApi.assignment(branch.id, { resource: resource.id, service_ids: services, is_active: active }),
    onSuccess: async () => {
      setSaved(JSON.stringify([active, [...services].sort()]));
      await Promise.all(["resources", "branch-catalog", "branch-configuration", "available-slots"].map(key => cache.invalidateQueries({ queryKey: [key] })));
    } });
  useEffect(() => { onDirtyChange(dirty || mutation.isPending); return () => onDirtyChange(false); }, [dirty, mutation.isPending, onDirtyChange]);
  const disabled = !branch.can_manage || !!branch.archived_at || !!resource.retired_at || mutation.isPending;
  return <form className="space-y-3" onSubmit={event => { event.preventDefault(); mutation.mutate(); }}>
    {mutation.error && <ErrorState error={mutation.error} />}
    <fieldset disabled={disabled} className="space-y-2">
      <label className="flex min-h-11 items-center gap-2 text-sm"><input type="checkbox" checked={active} onChange={event => setActive(event.target.checked)} />{t("branches.active")}</label>
      <fieldset className="space-y-1"><legend className="text-sm font-semibold">{t("branches.services")}</legend>
        {catalog.offers.map(offer => <label key={offer.id} className="flex min-h-11 items-center gap-2 text-sm"><input type="checkbox" checked={services.includes(offer.service)}
          onChange={event => setServices(event.target.checked ? [...services, offer.service] : services.filter(id => id !== offer.service))} />
          {offer.service_name}{!offer.is_active ? ` · ${t("branches.paused")}` : ""}</label>)}
      </fieldset>
      <Button type="submit" disabled={!dirty} isLoading={mutation.isPending}>{t("common.save")}</Button>
    </fieldset>
  </form>;
}

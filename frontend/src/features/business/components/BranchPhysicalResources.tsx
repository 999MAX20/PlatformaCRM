import { DraftGuard } from "../../../components/actions/DraftGuard";
import { useActionConfirm } from "../../../components/actions/ActionConfirmProvider";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";
import type { Branch, BranchConfiguration } from "../../../api/branches";
import { resourcesApi } from "../../../api/resources";
import { ResourceForm } from "../../../components/forms/ResourceForm";
import { Button } from "../../../components/ui/Button";
import { ErrorState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import type { Resource } from "../../../types";

export function BranchPhysicalResources({ branch, branches, config, disabled }: {
  branch: Branch; branches: Branch[]; config: BranchConfiguration; disabled: boolean;
}) {
  const { t } = useI18n();
  const confirm = useActionConfirm();
  const [dirty, setDirty] = useState(false);
  const client = useQueryClient();
  const [creating, setCreating] = useState(false);
  const mutation = useMutation({ mutationFn: (payload: Partial<Resource>) => resourcesApi.create(payload), onSuccess: async () => {
    await Promise.all(["resources", "branch-configuration", "branches", "available-slots"].map(key => client.invalidateQueries({ queryKey: [key] })));
    setDirty(false); setCreating(false);
  } });
  return <div className="space-y-4">
    <DraftGuard dirty={dirty} pending={mutation.isPending} />
    {config.physical_resources.length ? <ul className="divide-y divide-platforma-border">
      {config.physical_resources.map(resource => <li key={resource.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
        <div className="min-w-0"><p className="break-words text-sm font-semibold">{resource.name}</p>
          <p className="text-xs text-platforma-subtle">{t(`resources.type${resource.resource_type[0].toUpperCase()}${resource.resource_type.slice(1)}`)}{!resource.is_active ? ` · ${t("branches.unavailable")}` : ""}</p></div>
        <Link className="platforma-focus-ring inline-flex min-h-10 items-center text-sm font-semibold text-brand-700 underline" to={`/app/business/resources?resource=${resource.id}`}>{t("common.open")}</Link>
      </li>)}
    </ul> : <p className="text-sm text-platforma-subtle">{t("branches.noPhysicalResources")}</p>}
    {creating ? <div className="space-y-3 rounded-card border border-platforma-border p-4">
      {mutation.error && <ErrorState error={mutation.error} />}
      <ResourceForm businessId={branch.business} branches={branches} initial={{ resource_type: "equipment", branch: branch.id }} physicalOnly showContextHint={false} onDirtyChange={setDirty}
        disabled={disabled || mutation.isPending} onSubmit={payload => mutation.mutateAsync(payload)} />
      <Button variant="secondary" disabled={mutation.isPending} onClick={async () => { if (!dirty || (await confirm({ title: t("workingHours.discardChanges"), confirmLabel: t("actions.discardChanges"), tone: "warning" })).confirmed) { setDirty(false); setCreating(false); } }}>{t("common.cancel")}</Button>
    </div> : !disabled && <Button onClick={() => setCreating(true)}>{t("branches.addResource")}</Button>}
  </div>;
}

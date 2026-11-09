import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link } from "react-router";
import { branchesApi, type Branch, type BranchConfiguration } from "../../../api/branches";
import { useNotification } from "../../../components/notifications/NotificationProvider";
import { Button } from "../../../components/ui/Button";
import { ErrorState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import type { Id } from "../../../types";

export function ResourceRequirementForm({ branch, config, serviceId, disabled, onDirtyChange }: {
  branch: Branch; config: BranchConfiguration; serviceId: Id; disabled: boolean; onDirtyChange?: (dirty: boolean) => void;
}) {
  const { t } = useI18n();
  const client = useQueryClient();
  const notify = useNotification();
  const initialIds = config.resource_requirements.filter(row => row.service_id === serviceId).map(row => row.resource_id).sort((a, b) => a - b);
  const [selected, setSelected] = useState(initialIds);
  const [saved, setSaved] = useState(initialIds);
  const dirty = JSON.stringify([...selected].sort((a, b) => a - b)) !== JSON.stringify(saved);
  useEffect(() => { onDirtyChange?.(dirty); }, [dirty, onDirtyChange]);
  useEffect(() => () => onDirtyChange?.(false), [onDirtyChange]);
  const mutation = useMutation({ mutationFn: () => branchesApi.resourceRequirements(branch.id, { service: serviceId, resource_ids: selected }),
    onSuccess: async result => {
      setSaved([...result.resource_ids].sort((a, b) => a - b));
      await Promise.all(["branch-configuration", "branch-catalog", "available-slots", "branches"].map(key => client.invalidateQueries({ queryKey: [key] })));
      notify({ message: t("branches.requirementsSaved"), tone: "success" });
    } });
  const offered = config.offers.some(offer => offer.service === serviceId && offer.is_active);
  return <form className="space-y-3" onSubmit={event => { event.preventDefault(); mutation.mutate(); }}>
    <h3 className="text-sm font-semibold">{t("branches.requiredResources")}</h3>
    {!offered ? <p className="text-sm text-platforma-subtle">{t("branches.notOffered")}</p> : <>
      <p className="text-sm text-platforma-subtle">{t("branches.resourceRequirementHint")}</p>
      <fieldset disabled={disabled || mutation.isPending} className="space-y-1" aria-label={t("branches.requiredResources")}>
        {config.physical_resources.map(resource => <label key={resource.id} className="flex min-h-10 items-center gap-3 text-sm">
          <input type="checkbox" className="h-4 w-4 accent-brand-500" checked={selected.includes(resource.id)}
            disabled={!resource.is_active && !selected.includes(resource.id)}
            onChange={event => setSelected(event.target.checked ? [...selected, resource.id] : selected.filter(id => id !== resource.id))} />
          <span>{resource.name}{!resource.is_active ? ` · ${t("branches.unavailable")}` : ""}</span>
        </label>)}
        {!config.physical_resources.length && <p className="text-sm text-platforma-subtle">{t("branches.noPhysicalResources")}</p>}
      </fieldset>
      {!selected.length && <p className="text-sm text-platforma-subtle">{t("branches.noResourceRequirements")}</p>}
      {mutation.error && <ErrorState error={mutation.error} />}
      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" disabled={disabled || !dirty} isLoading={mutation.isPending}>{t("branches.saveRequirements")}</Button>
        <Link className="platforma-focus-ring text-sm font-semibold text-brand-700 underline" to="/app/business/resources">{t("nav.resources")}</Link>
      </div>
    </>}
  </form>;
}

import { useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router";
import { branchesApi, type Branch, type BranchConfiguration } from "../../../api/branches";
import { useActionConfirm } from "../../../components/actions/ActionConfirmProvider";
import { Button } from "../../../components/ui/Button";
import { Select } from "../../../components/ui/Select";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import type { Id, Service } from "../../../types";
import { ResourceRequirementForm } from "../../business/components/ResourceRequirementForm";
import { ServiceBranchTerms } from "../../business/components/ServiceBranchTerms";

export function ServiceResourceRequirements({ businessId, service, disabled, onDirtyChange }: {
  businessId: Id; service: Service; disabled: boolean; onDirtyChange: (dirty: boolean) => void;
}) {
  const { t } = useI18n();
  const confirm = useActionConfirm();
  const [params] = useSearchParams();
  const [selectedId, setSelectedId] = useState<Id | null>(Number(params.get("branch")) || null);
  const [dirty, setDirty] = useState(false);
  const reportDirty = useCallback((value: boolean) => { setDirty(value); onDirtyChange(value); }, [onDirtyChange]);
  const query = useQuery({ queryKey: ["branches", businessId], queryFn: () => branchesApi.listAll({ business: businessId }) });
  if (query.isLoading) return <LoadingState />;
  if (query.error) return <ErrorState error={query.error} action={<Button onClick={() => query.refetch()}>{t("common.retry")}</Button>} />;
  const locations = (query.data || []).filter(branch => branch.can_work || branch.can_manage);
  const selected = locations.find(branch => branch.id === selectedId) || locations[0];
  if (!selected) return null;
  return <section className="space-y-3 border-t border-platforma-border pt-4">
    {locations.length > 1 && <Select label={t("branches.branch")} value={selected.id} options={locations.map(branch => ({ value: branch.id, label: branch.name }))}
      onChange={async event => {
        const value = Number(event.target.value);
        if (dirty && !(await confirm({ title: t("workingHours.discardChanges"), confirmLabel: t("actions.discardChanges"), tone: "warning" })).confirmed) return;
        setSelectedId(value);
      }} />}
    <LocationRequirements key={`${selected.id}:${service.id}`} branch={selected} service={service} disabled={disabled || !selected.can_manage || !!selected.archived_at} onDirtyChange={reportDirty} />
  </section>;
}

function LocationRequirements({ branch, service, disabled, onDirtyChange }: {
  branch: Branch; service: Service; disabled: boolean; onDirtyChange: (dirty: boolean) => void;
}) {
  const { t } = useI18n();
  const [termsDirty, setTermsDirty] = useState(false);
  const [resourcesDirty, setResourcesDirty] = useState(false);
  useEffect(() => { onDirtyChange(termsDirty || resourcesDirty); return () => onDirtyChange(false); }, [termsDirty, resourcesDirty, onDirtyChange]);
  const query = useQuery({ queryKey: [branch.can_manage ? "branch-configuration" : "branch-catalog", branch.id], queryFn: async (): Promise<BranchConfiguration> => {
    if (branch.can_manage) return branchesApi.configuration(branch.id);
    const catalog = await branchesApi.catalog(branch.id);
    return { ...catalog, days: catalog.days || [], travel: [], physical_resources: catalog.physical_resources || [], resource_requirements: catalog.resource_requirements || [] };
  } });
  if (query.isLoading) return <LoadingState />;
  if (query.error) return <ErrorState error={query.error} action={<Button onClick={() => query.refetch()}>{t("common.retry")}</Button>} />;
  return query.data ? <div className="space-y-5">
    <ServiceBranchTerms branch={branch} service={service} config={query.data} disabled={disabled} onDirtyChange={setTermsDirty} />
    <ResourceRequirementForm branch={branch} serviceId={service.id} config={query.data}
      disabled={disabled || !branch.is_active} onDirtyChange={setResourcesDirty} />
    <div className="space-y-1 text-sm"><h3 className="font-semibold">{t("business.staff")}</h3>
      {query.data.assignments.filter(item => item.service_ids.includes(service.id)).map(item => <p key={item.id}>{item.resource_name}{!item.is_active ? ` · ${t("branches.paused")}` : ""}</p>)}
    </div>
  </div> : null;
}

import { useQuery } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { branchesApi, type Branch } from "../../../api/branches";
import { useActionConfirm } from "../../../components/actions/ActionConfirmProvider";
import { Button } from "../../../components/ui/Button";
import { Select } from "../../../components/ui/Select";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import type { Id } from "../../../types";
import { ResourceRequirementForm } from "../../business/components/ResourceRequirementForm";

export function ServiceResourceRequirements({ businessId, serviceId, disabled, onDirtyChange }: {
  businessId: Id; serviceId: Id; disabled: boolean; onDirtyChange: (dirty: boolean) => void;
}) {
  const { t } = useI18n();
  const confirm = useActionConfirm();
  const [selectedId, setSelectedId] = useState<Id | null>(null);
  const [dirty, setDirty] = useState(false);
  const reportDirty = useCallback((value: boolean) => { setDirty(value); onDirtyChange(value); }, [onDirtyChange]);
  const query = useQuery({ queryKey: ["branches", businessId], queryFn: () => branchesApi.listAll({ business: businessId }) });
  if (query.isLoading) return <LoadingState />;
  if (query.error) return <ErrorState error={query.error} action={<Button onClick={() => query.refetch()}>{t("common.retry")}</Button>} />;
  const locations = (query.data || []).filter(branch => !branch.archived_at && branch.can_manage);
  const selected = locations.find(branch => branch.id === selectedId) || locations[0];
  if (!selected) return null;
  return <section className="space-y-3 border-t border-platforma-border pt-4">
    {locations.length > 1 && <Select label={t("branches.branch")} value={selected.id} options={locations.map(branch => ({ value: branch.id, label: branch.name }))}
      onChange={async event => {
        const value = Number(event.target.value);
        if (dirty && !(await confirm({ title: t("workingHours.discardChanges"), confirmLabel: t("actions.discardChanges"), tone: "warning" })).confirmed) return;
        setSelectedId(value);
      }} />}
    <LocationRequirements key={`${selected.id}:${serviceId}`} branch={selected} serviceId={serviceId} disabled={disabled} onDirtyChange={reportDirty} />
  </section>;
}

function LocationRequirements({ branch, serviceId, disabled, onDirtyChange }: {
  branch: Branch; serviceId: Id; disabled: boolean; onDirtyChange: (dirty: boolean) => void;
}) {
  const { t } = useI18n();
  const query = useQuery({ queryKey: ["branch-configuration", branch.id], queryFn: () => branchesApi.configuration(branch.id) });
  if (query.isLoading) return <LoadingState />;
  if (query.error) return <ErrorState error={query.error} action={<Button onClick={() => query.refetch()}>{t("common.retry")}</Button>} />;
  return query.data ? <ResourceRequirementForm branch={branch} serviceId={serviceId} config={query.data}
    disabled={disabled || !branch.is_active} onDirtyChange={onDirtyChange} /> : null;
}

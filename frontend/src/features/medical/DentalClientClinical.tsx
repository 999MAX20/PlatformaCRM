import { ActualVisitEntry } from "./ActualVisitEntry";
import { useQuery } from "@tanstack/react-query";
import { useCallback, useImperativeHandle, useRef, useState, type Ref } from "react";
import { branchesApi } from "../../api/branches";
import { Button } from "../../components/ui/Button";
import { Select } from "../../components/ui/Select";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { ClientClinicalEntry } from "./ClientClinicalEntry";
import type { ClinicalEntryHandle } from "./ClinicalAppointmentEntry";
import { PatientParticipationEntry } from "./ParticipationEntry";

export function DentalClientClinical({ businessId, clientId, userId, navigationRef, onDirtyChange }: {
  businessId: number; clientId: number; userId: number; navigationRef: Ref<ClinicalEntryHandle>; onDirtyChange: (dirty: boolean) => void;
}) {
  const { t } = useI18n();
  const [branch, setBranch] = useState("");
  const clinical = useRef<ClinicalEntryHandle>(null);
  const actualOpen = useRef(false);
  const onActualOpen = useCallback((value: boolean) => { actualOpen.current = value; onDirtyChange(value); }, [onDirtyChange]);
  useImperativeHandle(navigationRef, () => ({ beforeLeave: () => actualOpen.current ? Promise.resolve(false) : clinical.current?.beforeLeave() ?? Promise.resolve(true) }));
  const query = useQuery({ queryKey: ["medical-branch-options", businessId, userId], queryFn: () => branchesApi.listAll({ business: businessId }) });
  const available = (query.data ?? []).filter(item => item.is_active && !item.archived_at && item.can_work);
  const selected = branch || (available.length === 1 ? String(available[0].id) : "");
  const valid = available.some(item => String(item.id) === selected);
  if (query.isPending) return <LoadingState />;
  if (query.error) return <ErrorState error={query.error} action={<Button onClick={() => void query.refetch()}>{t("common.retry")}</Button>} />;
  return <div className="space-y-4">
    <Select label={t("medical.branch")} value={selected} options={[
      { value: "", label: t("medical.selectBranch") }, ...available.map(item => ({ value: item.id, label: item.name })),
    ]} onChange={event => { const next = event.target.value; void (async () => {
      if (await (clinical.current?.beforeLeave() ?? Promise.resolve(true))) setBranch(next);
    })(); }} />
    {valid ? <>
      <ActualVisitEntry key={`actual:${selected}`} scope={{ business_id: businessId, client_id: clientId, branch_id: Number(selected) }}
        beforeOpen={() => clinical.current?.beforeLeave() ?? Promise.resolve(true)} onOpenChange={onActualOpen} />
      <ClientClinicalEntry key={selected} businessId={businessId} clientId={clientId} branchId={Number(selected)} embedded navigationRef={clinical} onDirtyChange={onDirtyChange} />
      <div className="border-t border-platforma-border pt-4">
        <PatientParticipationEntry key={`team:${selected}`} businessId={businessId} clientId={clientId} branchId={Number(selected)} />
      </div>
    </> : <p className="text-sm text-platforma-subtle">{t("medical.selectBranch")}</p>}
  </div>;
}

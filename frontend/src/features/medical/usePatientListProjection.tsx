import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import { medicalPatientsApi as api, type PatientListStatus } from "../../api/medicalPatients";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Select } from "../../components/ui/Select";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import type { Id } from "../../types";

export function usePatientListProjection(businessId: number, userId: number, clientIds: number[], enabled: boolean) {
  const { t } = useI18n();
  const owner = `${businessId}:${userId}`;
  const [selection, setSelection] = useState({ owner, branch: "" });
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<{ key: string; rows?: PatientListStatus[]; error?: unknown } | null>(null);
  const access = useQuery({ queryKey: ["medical-patient-search-access", businessId, userId],
    queryFn: ({ signal }) => api.searchAccess(businessId, signal), enabled, retry: false });
  const branches = enabled && !access.isError ? access.data?.branches ?? [] : [];
  const branch = (selection.owner === owner ? selection.branch : "") || (branches.length === 1 ? String(branches[0].id) : "");
  const valid = branches.some(item => String(item.id) === branch);
  const ids = JSON.stringify(clientIds);
  const key = `${owner}:${branch}:${ids}:${attempt}`;
  useEffect(() => {
    if (!enabled || !valid) return;
    const controller = new AbortController();
    const selectedIds: number[] = JSON.parse(ids);
    setResult(null);
    async function read() {
      try {
        const rows: PatientListStatus[] = [];
        for (let index = 0; index < selectedIds.length; index += 100) {
          rows.push(...await api.listProjection({ business_id: businessId, branch_id: Number(branch) }, selectedIds.slice(index, index + 100), controller.signal));
        }
        if (!controller.signal.aborted) setResult({ key, rows });
      } catch (error) { if (!controller.signal.aborted) setResult({ key, error }); }
    }
    void read();
    return () => controller.abort();
  }, [businessId, branch, enabled, ids, key, valid]);
  if (!enabled || (axios.isAxiosError(access.error) && access.error.response?.status === 403)) return { columns: [], controls: null };
  const current = result?.key === key && valid ? result : null;
  const error = access.error || current?.error;
  const denied = axios.isAxiosError(error) && [401, 403].includes(error.response?.status ?? 0);
  const byClient = new Map(current?.rows?.map(row => [row.client_id, row]) ?? []);
  const columns = current?.rows && !error ? [{ id: "medical-record-status", header: t("medical.list.status"), cell: (client: { id: Id }) => {
    const status = byClient.get(Number(client.id));
    return status ? [t(status.has_record ? "medical.list.present" : "medical.list.absent"),
      status.identity_status ? t(`medical.${status.identity_status}`) : ""].filter(Boolean).join(" · ") : "";
  } }] : [];
  const retry = () => { if (access.error) void access.refetch(); setAttempt(value => value + 1); };
  const controls = branches.length || error ? <div className="space-y-3" data-testid="medical-list-controls">
    <div className="flex flex-wrap items-end gap-3">
      {branches.length ? <Select label={t("medical.list.branch")} value={branch} className="w-full sm:w-72" onChange={event => setSelection({ owner, branch: event.target.value })}
        options={[{ value: "", label: t("medical.selectBranch") }, ...branches.map(item => ({ value: item.id, label: item.name }))]} /> : null}
      {valid ? <Button variant="secondary" size="lg" onClick={() => { if (current || error) retry(); }} aria-disabled={!current && !error}>{t("medical.clinical.reload")}</Button> : null}
    </div>
    {error ? <ErrorState message={denied ? t("medical.denied") : getApiErrorMessage(error)} action={!denied ? <Button variant="secondary" onClick={retry}>{t("common.retry")}</Button> : undefined} /> : valid && !current ? <LoadingState /> : null}
  </div> : null;
  return { columns, controls };
}

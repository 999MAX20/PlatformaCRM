import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { importExportApi } from "../../api/importExport";
import { analyticsExports } from "../../api/analyticsExports";
import type { CustomFieldEntityType, Id } from "../../types";
import { useI18n } from "../../lib/i18n";
import { Button } from "../ui/Button";
import { ErrorState } from "../ui/StateViews";
import { useAuth } from "../../features/auth/AuthProvider";

export function EntityExportButton({ business, kind, label }: { business: Id; kind: CustomFieldEntityType; label?: string }) {
  const { user } = useAuth();
  const { t } = useI18n(); const [jobId, setJobId] = useState<Id | null>(null);
  const [busy, setBusy] = useState(false); const [error, setError] = useState<unknown>(null);
  const entity = ({ client: "clients", service: "services", specialist: "specialists", appointment: "appointments", lead: "leads", deal: "deals" } as const)[kind];
  const job = useQuery({ queryKey: ["entity-export", business, user?.id, kind, jobId], queryFn: () => analyticsExports.job(jobId!, business), enabled: !!jobId,
    refetchInterval: query => ["pending", "running"].includes(query.state.data?.status || "pending") && !query.state.error ? 3000 : false });
  const request = async () => {
    setBusy(true); setError(null);
    try { const next = await importExportApi.exportEntity({ business, entity }); setJobId(next?.id || null); }
    catch (failure) { setError(failure); }
    finally { setBusy(false); }
  };
  return <div className="flex flex-wrap items-center gap-2">
    <Button size="sm" variant="secondary" disabled={busy || (jobId !== null && !job.error && ["pending", "running"].includes(job.data?.status || "pending"))} onClick={() => void request()}>{label || t("importWorkspace.exportAll")}</Button>
    {jobId !== null && !job.error && ["pending", "running"].includes(job.data?.status || "pending") && <span role="status" className="text-sm">{t("importWorkspace.processing")}</span>}
    {job.data?.status === "failed" && <p role="alert" className="text-sm text-platforma-danger">{t("importWorkspace.exportFailed")}</p>}
    {job.data?.status === "succeeded" && !job.error && <Button size="sm" disabled={busy} onClick={async () => {
      setBusy(true); setError(null); try { await analyticsExports.download(jobId!, business); } catch (failure) { setError(failure); } finally { setBusy(false); }
    }}>{t("importWorkspace.download")}</Button>}
    {(error || job.error) && <ErrorState error={error || job.error} />}
  </div>;
}

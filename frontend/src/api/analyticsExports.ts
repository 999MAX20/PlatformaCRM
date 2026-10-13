import { apiClient } from "./client";
import type { Id } from "../types";
import type { AnalyticsExportJob, AnalyticsPeriod, WorkspaceReport } from "../types/analyticsWorkspace";

function saveCsv(data: Blob, filename: string) {
  const url = URL.createObjectURL(data);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export const analyticsExports = {
  request: async (business: Id, period: AnalyticsPeriod, report: WorkspaceReport): Promise<AnalyticsExportJob | null> => {
    const response = await apiClient.get<Blob>("/api/analytics/reports/export/", {
      params: { business, ...period, report }, responseType: "blob",
    });
    if (response.status === 202) {
      const job: AnalyticsExportJob = JSON.parse(await response.data.text());
      if (!job.id || !["pending", "running", "succeeded", "failed"].includes(job.status)) throw new Error("Invalid export response");
      return job;
    }
    saveCsv(response.data, `${report}-${period.start}-${period.end}.csv`);
    return null;
  },
  job: async (id: Id, business: Id) => {
    const { data } = await apiClient.get<AnalyticsExportJob>(`/api/export-jobs/${id}/`, { params: { business } });
    return data;
  },
  download: async (id: Id, business: Id) => {
    const { data } = await apiClient.get<Blob>(`/api/export-jobs/${id}/download/`, { params: { business }, responseType: "blob" });
    saveCsv(data, `analytics-${id}.csv`);
  },
};

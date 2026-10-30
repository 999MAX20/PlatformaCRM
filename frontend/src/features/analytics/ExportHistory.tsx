import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { analyticsExports } from "../../api/analyticsExports";
import { CrmPagination } from "../../components/crm/CrmPagination";
import { Button } from "../../components/ui/Button";
import { Select } from "../../components/ui/Select";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import type { Business, Id } from "../../types";

const kinds = ["entity", "analytics_report"];
const statuses = ["pending", "running", "succeeded", "failed"];
const reports: Record<string, string> = {
  clients: "clients.title", leads: "leads.title", deals: "deals.title",
  sales: "status.sales", catalog: "integrations.import.catalogShort",
  source_roi: "analytics.sourceRoi",
  workspace_overview: "analyticsWorkspace.overview", workspace_sources: "analyticsWorkspace.sources",
  workspace_services: "analyticsWorkspace.services", workspace_team: "analyticsWorkspace.team",
  workspace_finance: "analyticsWorkspace.finance",
};

export function ExportHistory({ business, userId }: { business: Business; userId: Id }) {
  const { t, language } = useI18n();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [kind, setKind] = useState("");
  const [status, setStatus] = useState("");
  const history = useQuery({
    queryKey: ["export-history", userId, business.id, kind, status, page, pageSize],
    queryFn: () => analyticsExports.history({ business: business.id, page, page_size: pageSize, kind: kind || undefined, status: status || undefined }),
    retry: false,
    // Poll filtered pages too: an in-progress job can move into or out of them.
    refetchInterval: query => query.state.error ? false : 5000,
  });
  const download = useMutation({ mutationFn: (id: Id) => analyticsExports.download(id, business.id) });
  const rows = history.data?.results ?? [];
  return <div className="space-y-4" data-testid="export-history">
    <div className="flex flex-wrap items-end gap-3">
      <Select label={t("exportHistory.kind")} value={kind} onChange={event => { setKind(event.target.value); setPage(1); download.reset(); }}
        options={[{ value: "", label: t("common.all") }, ...kinds.map(value => ({ value, label: t(`exportHistory.kind.${value}`) }))]} />
      <Select label={t("exportHistory.status")} value={status} onChange={event => { setStatus(event.target.value); setPage(1); download.reset(); }}
        options={[{ value: "", label: t("common.all") }, ...statuses.map(value => ({ value, label: t(`exportHistory.status.${value}`) }))]} />
      <Button variant="secondary" disabled={history.isFetching} onClick={() => void history.refetch()}>{t("analyticsWorkspace.refresh")}</Button>
    </div>
    {download.error ? <ErrorState error={download.error} /> : null}
    {history.isPending ? <LoadingState /> : history.error ? <ErrorState error={history.error} action={<Button onClick={() => void history.refetch()}>{t("analyticsWorkspace.refresh")}</Button>} /> : <>
      {rows.length === 0 ? <EmptyState title={t("exportHistory.empty")} /> : <ul className="divide-y divide-platforma-border" aria-busy={history.isFetching}>
        {rows.map(job => <li key={job.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
          <div className="min-w-0 space-y-1 text-sm">
            <p className="font-semibold">{t(reports[job.export_key] || `exportHistory.kind.${job.kind}`)} · #{job.id}</p>
            <p className="text-platforma-subtle">{new Intl.DateTimeFormat(language, { dateStyle: "short", timeStyle: "short", timeZone: business.timezone }).format(new Date(job.created_at))}</p>
            {job.parameters_json.start && job.parameters_json.end ? <p>{job.parameters_json.start} — {job.parameters_json.end}</p> : null}
            <p>{t(`exportHistory.status.${job.status}`)} · {t("exportHistory.rows", { count: job.row_count })}</p>
          </div>
          {job.status === "succeeded" && job.download_url ? <Button variant="secondary" disabled={download.isPending} onClick={() => download.mutate(job.id)}>{t("analyticsWorkspace.download")}</Button> : null}
        </li>)}
      </ul>}
      <CrmPagination compact shown={rows.length} total={history.data?.count ?? 0} page={page} pageSize={pageSize}
        onPageChange={value => { setPage(value); download.reset(); }} onPageSizeChange={setPageSize} pageSizePortal={false}
        previousLabel={t("pagination.previous")} nextLabel={t("pagination.next")} />
    </>}
  </div>;
}

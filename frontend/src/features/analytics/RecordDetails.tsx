import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";
import { analyticsApi } from "../../api/analytics";
import { normalizeAppError } from "../../api/appError";
import { CrmPagination } from "../../components/crm/CrmPagination";
import { Button } from "../../components/ui/Button";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { formatDateTime } from "../../lib/format";
import { useI18n } from "../../lib/i18n";
import type { Business, Id } from "../../types";
import type { WorkspaceRecordSelection } from "../../types/analyticsWorkspace";
import { ReportTable } from "./WorkspaceSections";

export function RecordDetails({ business, userId, selection }: { business: Business; userId: Id; selection: WorkspaceRecordSelection }) {
  const { t, language } = useI18n();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const records = useQuery({
    queryKey: ["analytics-records", userId, business.id, selection.period, selection.filters, page, pageSize],
    queryFn: ({ signal }) => analyticsApi.records(business.id, selection.period, selection.filters, page, pageSize, signal), retry: false,
  });
  const category = records.error ? normalizeAppError(records.error).category : null;
  return <div className="space-y-4" data-testid="analytics-record-details">
    <p className="text-sm text-platforma-subtle">{selection.period.start} — {selection.period.end} · {business.timezone}</p>
    {records.isPending ? <LoadingState /> : records.error ? <ErrorState error={records.error} action={category === "permission" || category === "authentication" ? undefined : <Button variant="secondary" onClick={() => void records.refetch()}>{t("analyticsWorkspace.refresh")}</Button>} /> : records.data ? <>
      <ReportTable title={selection.title} columns={[t("appointments.title"), t("nav.clients"), t("analyticsWorkspace.service"), t("appointment.status"), t("appointment.responsible")]}
        rows={records.data.results.map(row => [
          <Link className="platforma-focus-ring inline-flex min-h-11 items-center underline underline-offset-4" to={`/app/appointments/${row.id}`}>{formatDateTime(row.start_at, business.timezone, true, language)}</Link>,
          row.client_name || "—", row.service_name, <span>{t(`status.${row.status}`)}{row.is_archived ? <span className="block text-xs text-platforma-subtle">{t("analyticsWorkspace.archivedRecord")}</span> : null}</span>, row.responsible_user_name || "—",
        ])} />
      <CrmPagination compact shown={records.data.results.length} total={records.data.count} page={page} pageSize={pageSize} onPageChange={setPage} onPageSizeChange={setPageSize} previousLabel={t("pagination.previous")} nextLabel={t("pagination.next")} />
    </> : null}
  </div>;
}

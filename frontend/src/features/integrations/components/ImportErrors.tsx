import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { importExportApi } from "../../../api/importExport";
import { CrmPagination } from "../../../components/crm/CrmPagination";
import { Button } from "../../../components/ui/Button";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import type { Id, ImportJob } from "../../../types";

export function ImportErrors({ job, userId }: { job: ImportJob; userId: Id }) {
  const { t } = useI18n();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const query = useQuery({
    queryKey: ["import-errors", userId, job.business, job.id, job.updated_at, page, pageSize],
    queryFn: () => importExportApi.errors(job.id, page, pageSize),
    retry: false,
  });
  if (query.isError) return <ErrorState error={query.error} action={<Button variant="secondary" onClick={() => query.refetch()}>{t("common.retry")}</Button>} />;
  if (query.isPending) return <LoadingState />;
  return <section className="mt-4 space-y-2" aria-label={t("integrations.import.summaryErrors")}>
    <p className="text-sm font-semibold text-platforma-danger">{t("integrations.import.fixFileShort")}</p>
    <ul className="space-y-2 text-sm text-platforma-danger" data-testid="import-errors">
      {query.data.results.map((item, index) => <li key={`${item.row}-${item.field}-${index}`} className="break-words">
        {t("integrations.import.rowError", { row: item.row, field: t(`integrations.import.fields.${item.field}`), message: errorMessage(item.message, t) })}
      </li>)}
    </ul>
    <CrmPagination shown={query.data.results.length} total={query.data.count} page={page} pageSize={pageSize}
      onPageChange={setPage} onPageSizeChange={setPageSize} previousLabel={t("pagination.previous")} nextLabel={t("pagination.next")} compact />
  </section>;
}

function errorMessage(message: string, t: ReturnType<typeof useI18n>["t"]) {
  const keys: Record<string, string> = {
    "Amount must be a number.": "amount", "Quantity must be a number.": "quantity",
    "Price must be a number.": "price", "Stock quantity must be a number.": "stock",
    "Name is required.": "name", "Duration must be a positive integer.": "duration",
    "Use ISO datetime, for example 2026-05-22T10:00:00+05:00.": "datetime",
    "Select at least one column mapping.": "mapping", "Invalid lead status.": "status",
    "Reason is required when lead is lost.": "lostReason", "Loss reason is only allowed for a lost lead.": "unexpectedReason",
  };
  if (keys[message]) return t(`integrations.import.validation.${keys[message]}`);
  if (/^Required column for \w+ is missing\.$/.test(message)) return t("integrations.import.validation.requiredColumn");
  return message;
}

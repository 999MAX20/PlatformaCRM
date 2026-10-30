import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { importExportApi, type ImportEntity } from "../../../api/importExport";
import type { Id, ImportJob } from "../../../types";

// ImportPanel keys this hook's owner by user, business and entity.
export function useImportHistory(userId: Id, businessId: Id, entity: ImportEntity) {
  const client = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [selection, setSelection] = useState<Id | null>(null);
  const context = { business: businessId, entity_type: entity };
  const matches = (job: ImportJob) => String(job.business) === String(businessId) && job.entity_type === entity;
  const detailKey = (id: Id) => ["import-job", userId, businessId, entity, id];
  const query = useQuery({
    queryKey: ["import-jobs", userId, businessId, entity, page, pageSize],
    queryFn: () => importExportApi.importJobs({ ...context, page, page_size: pageSize }),
    retry: false,
  });
  const jobs = query.isError ? [] : (query.data?.results || []).filter(matches);
  const selectedId = selection ?? jobs[0]?.id;
  const detail = useQuery({
    queryKey: detailKey(selectedId ?? ""),
    queryFn: () => importExportApi.getImportJob(selectedId!, context),
    enabled: selectedId != null && !query.isError,
    retry: false,
    // Background focus refresh must not discard an in-progress mapping edit.
    refetchOnWindowFocus: false,
  });
  const selected = !query.isError && !detail.isError && !detail.isFetching && detail.data && matches(detail.data)
    && String(detail.data.id) === String(selectedId) ? detail.data : undefined;
  function changePage(value: number) { setSelection(null); setPage(value); }
  function select(id: Id) {
    void client.invalidateQueries({ queryKey: detailKey(id) });
    setSelection(id);
  }
  function changePageSize(value: number) { setSelection(null); setPage(1); setPageSize(value); }
  function accept(job: ImportJob, firstPage = false) {
    if (!matches(job)) return;
    client.setQueryData(detailKey(job.id), job);
    setSelection(job.id);
    if (firstPage) setPage(1);
    void client.invalidateQueries({ queryKey: ["import-jobs", userId, businessId, entity] });
  }
  return { query, detail, jobs, selected, selectedId, page, pageSize, changePage, changePageSize, select, accept };
}

import { useEffect, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FileSpreadsheet, Upload } from "lucide-react";

import { getApiErrorMessage } from "../../../api/client";
import { importExportApi, type ImportEntity } from "../../../api/importExport";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { StatusNotice } from "../../../components/ui/StatusNotice";
import { cn } from "../../../lib/cn";
import { useI18n } from "../../../lib/i18n";
import type { Id, ImportJob } from "../../../types";

import { hasPermission } from "../../../lib/permissions";
import { useAuth } from "../../auth/AuthProvider";
import { ImportJobReview } from "./ImportJobReview";
import { useImportHistory } from "./useImportHistory";
import { CrmPagination } from "../../../components/crm/CrmPagination";

type Translate = ReturnType<typeof useI18n>["t"];

function importStatusLabel(status: string | undefined, t: Translate) {
  const labels: Record<string, string> = {
    uploaded: "integrations.import.status.uploaded",
    previewed: "integrations.import.status.previewed",
    imported: "integrations.import.status.imported",
    failed: "integrations.import.status.failed",
    cancelled: "integrations.import.status.cancelled",
  };
  return status ? t(labels[status] || status) : t("integrations.import.status.none");
}

function ImportMetric({ label, value, tone = "default" }: { label: string; value?: number | string; tone?: "default" | "danger" | "success" }) {
  return (
    <div className={cn(
      "rounded-control px-3 py-2",
      tone === "danger" ? "bg-[var(--platforma-danger-soft)] text-platforma-danger" : tone === "success" ? "bg-[var(--platforma-success-soft)] text-platforma-success" : "bg-surface-card text-platforma-subtle",
    )}>
      <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-platforma-faint">{label}</p>
      <p className="mt-1 text-lg font-semibold">{value ?? 0}</p>
    </div>
  );
}

const importEntities: ImportEntity[] = ["clients", "leads", "deals", "sales", "catalog"];

type ImportPanelProps = {
  businessId: Id;
  allowedEntities?: ImportEntity[];
  initialEntity?: ImportEntity;
  onImported?: (job: ImportJob) => void;
};

export function ImportPanel(props: ImportPanelProps) {
  const { user } = useAuth();
  if (!user) return null;
  return <ScopedImportPanel key={`${user.id}:${props.businessId}:${props.allowedEntities?.join(",")}:${props.initialEntity}`} {...props} userId={user.id} />;
}

function ScopedImportPanel(props: ImportPanelProps & { userId: Id }) {
  const allowed = props.allowedEntities?.length ? props.allowedEntities : importEntities;
  const [entity, setEntity] = useState<ImportEntity>(props.initialEntity && allowed.includes(props.initialEntity) ? props.initialEntity : allowed[0]);
  return <ImportPanelBody key={entity} {...props} normalizedEntities={allowed} entity={entity} setEntity={setEntity} />;
}

function ImportPanelBody({ businessId, userId, normalizedEntities, entity, setEntity, onImported }: ImportPanelProps & {
  userId: Id; normalizedEntities: ImportEntity[]; entity: ImportEntity; setEntity: (entity: ImportEntity) => void;
}) {
  const { t } = useI18n();
  const { user } = useAuth();
  const canCreate = hasPermission(user, businessId, entity === "sales" || entity === "catalog" ? "integrations" : entity, "create");
  const queryClient = useQueryClient();
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const [fileKey, setFileKey] = useState(0);
  const [file, setFile] = useState<File | null>(null);
  const history = useImportHistory(userId, businessId, entity);
  const { query: jobsQuery, jobs, selected } = history;

  const upload = useMutation({
    mutationFn: () => {
      if (!file) throw new Error(t("integrations.import.chooseFile"));
      return importExportApi.upload({ business: businessId, entity, file });
    },
    onSuccess: (job) => {
      if (!mounted.current) return;
      history.accept(job, true);
      setFile(null);
      setFileKey(value => value + 1);
    },
  });

  function updateJob(job: ImportJob) {
    if (!mounted.current) return;
    history.accept(job);
  }
  function imported(job: ImportJob) {
    if (!mounted.current) return;
    updateJob(job);
    for (const key of ["clients", "leads", "deals", "services", "connector-sync-runs"]) {
      queryClient.invalidateQueries({ queryKey: [key] });
    }
    onImported?.(job);
  }

  const template = useMutation({
    mutationFn: importExportApi.downloadTemplate,
  });

  const errors = selected?.errors_json?.rows || [];
  const duplicates = selected?.duplicates_json?.rows || [];
  const summary = selected?.summary_json || selected?.preview_json?.import_summary;
  const importError = jobsQuery.error || upload.error || template.error;
  const entityOptions = [
    { value: "clients", label: t("integrations.import.clients") },
    { value: "leads", label: t("integrations.import.leads") },
    { value: "deals", label: t("integrations.import.deals") },
    { value: "sales", label: t("integrations.import.sales") },
    { value: "catalog", label: t("integrations.import.catalogShort") },
  ].filter((option) => normalizedEntities.includes(option.value as ImportEntity));

  return (
    <div className="space-y-4" onKeyDown={event => {
      // Select handles Escape first; keep that key from closing the import dialog.
      if (event.key === "Escape" && event.defaultPrevented) event.stopPropagation();
    }}>
      <div className="rounded-card border border-platforma-border bg-surface-card p-4 shadow-xs">
        <p className="text-sm font-semibold text-platforma-ink">Excel / CSV</p>
        <p className="mt-1 text-sm font-medium leading-6 text-platforma-muted">
          {t("integrations.import.panelDescription")}
        </p>
      </div>

      {importError ? <ErrorState error={importError} message={getApiErrorMessage(importError)} action={jobsQuery.isError ? <Button variant="secondary" onClick={() => jobsQuery.refetch()}>{t("common.retry")}</Button> : undefined} /> : null}
      {jobsQuery.isPending ? <LoadingState /> : null}
      {history.detail.isFetching ? <LoadingState /> : null}
      {history.detail.isError && !jobsQuery.isError ? <ErrorState error={history.detail.error} action={<Button variant="secondary" onClick={() => history.detail.refetch()}>{t("common.retry")}</Button>} /> : null}

      <div className="rounded-card border border-platforma-border bg-surface-card p-4 shadow-xs">
        <div className="grid gap-3 lg:grid-cols-[180px_1fr_auto_auto]">
          <Select
            data-testid="import-entity"
            aria-label={t("integrations.import.entity")}
            value={entity}
            disabled={entityOptions.length === 1}
            onChange={(event) => setEntity(event.target.value as ImportEntity)}
            options={entityOptions}
          />
          <Input
            key={fileKey}
            data-testid="import-file"
            aria-label={t("integrations.import.chooseFile")}
            type="file"
            accept=".csv,.xlsx"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
          />
          <Button type="button" variant="secondary" isLoading={template.isPending} onClick={() => template.mutate(entity)}>
            <FileSpreadsheet size={16} /> {t("integrations.import.template")}
          </Button>
          <Button
            data-testid="import-preview"
            type="button"
            disabled={!canCreate || !file || upload.isPending}
            isLoading={upload.isPending}
            onClick={() => upload.mutate()}
          >
            <Upload size={16} /> {t("integrations.import.checkFile")}
          </Button>
        </div>
      </div>

      <div className="rounded-card border border-platforma-border bg-surface-card p-4 shadow-xs">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="font-semibold text-platforma-ink">{selected?.original_filename || t("integrations.import.noFileSelected")}</p>
            <p className="mt-1 text-sm text-platforma-muted">
              {selected
                ? t("integrations.import.fileMeta", {
                    entity: entityOptions.find(option => option.value === selected.entity_type)?.label || selected.entity_type,
                    rows: selected.total_rows,
                    status: importStatusLabel(selected.status, t),
                  })
                : t("integrations.import.noFileSelectedText")}
            </p>
          </div>

        </div>

        {selected ? (
          <div className="mt-4 grid gap-2 sm:grid-cols-4">
            <ImportMetric label={t("integrations.import.summaryRows")} value={summary?.total_rows ?? selected.total_rows} />
            <ImportMetric label={t("integrations.import.summaryErrors")} value={summary?.errors ?? errors.length} tone={errors.length ? "danger" : "default"} />
            <ImportMetric label={t("integrations.import.summaryDuplicates")} value={summary?.duplicates ?? duplicates.length} />
            <ImportMetric label={t("integrations.import.summaryImported")} value={summary?.imported ?? selected.imported_count} tone={selected.status === "imported" ? "success" : "default"} />
          </div>
        ) : null}

        {duplicates.length ? (
          <StatusNotice
            data-testid="import-duplicates"
            className="mt-4"
            compact
            tone="warning"
            title={t("integrations.import.duplicatesFound")}
            description={t("integrations.import.duplicatesDescription")}
          />
        ) : null}

        {selected ? <ImportJobReview key={`${selected.id}:${selected.updated_at}`} job={selected} userId={userId} canCreate={canCreate && !upload.isPending && !file} onChange={updateJob} onImported={imported} /> : null}

      </div>

      <div className="rounded-card border border-platforma-border bg-surface-card p-4 shadow-xs">
        <p className="font-semibold text-platforma-ink">{t("integrations.import.history")}</p>
        <div className="mt-3 space-y-2">
          {jobs.map((job) => (
            <button
              key={job.id}
              type="button"
              onClick={() => history.select(job.id)}
              aria-pressed={String(history.selectedId) === String(job.id)}
              className="platforma-focus-ring w-full rounded-control bg-surface-muted px-3 py-2 text-left text-sm transition hover:bg-surface-hover"
            >
              <span className="block break-words font-semibold text-platforma-ink">{job.original_filename}</span>
              <span className="font-semibold text-platforma-ink">#{job.id} {entityOptions.find(option => option.value === job.entity_type)?.label}</span>
              <span className="ml-2 text-platforma-muted">{importStatusLabel(job.status, t)} · {job.imported_count}/{job.total_rows}</span>
            </button>
          ))}
          {!jobsQuery.isLoading && !jobsQuery.isError && !jobs.length ? <p className="text-sm text-platforma-muted">{t("integrations.import.noImports")}</p> : null}
        </div>
        {!jobsQuery.isPending && !jobsQuery.isError ? <CrmPagination compact pageSizePortal={false}
          shown={jobs.length} total={jobsQuery.data?.count ?? 0} page={history.page} pageSize={history.pageSize}
          onPageChange={history.changePage} onPageSizeChange={history.changePageSize}
          previousLabel={t("pagination.previous")} nextLabel={t("pagination.next")} /> : null}
      </div>
    </div>
  );
}

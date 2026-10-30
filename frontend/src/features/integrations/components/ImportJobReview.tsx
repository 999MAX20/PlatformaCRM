import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { importExportApi } from "../../../api/importExport";
import { Button } from "../../../components/ui/Button";
import { Select } from "../../../components/ui/Select";
import { ErrorState } from "../../../components/ui/StateViews";
import { StatusNotice } from "../../../components/ui/StatusNotice";
import { useI18n } from "../../../lib/i18n";
import type { Id, ImportJob } from "../../../types";
import { ImportErrors } from "./ImportErrors";
import { canConfirmImport, sameImportMapping } from "./importReviewModel";

export function ImportJobReview({ job, userId, canCreate, onChange, onImported }: {
  job: ImportJob; userId: Id; canCreate: boolean; onChange: (job: ImportJob) => void; onImported: (job: ImportJob) => void;
}) {
  const { t } = useI18n();
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const [mapping, setMapping] = useState(job.mapping_json);
  const preview = useMutation({ mutationFn: () => importExportApi.preview(job.id, mapping),
    onSuccess: result => { if (mounted.current) onChange(result); } });
  const confirm = useMutation({ mutationFn: () => importExportApi.confirm(job.id),
    onSuccess: result => { if (mounted.current) onImported(result); } });
  const busy = preview.isPending || confirm.isPending;
  const editable = canCreate && job.status !== "imported" && job.status !== "cancelled";
  const dirty = !sameImportMapping(mapping, job.mapping_json);
  const errors = job.errors_json?.count ?? job.errors_json?.rows?.length ?? 0;
  const rows = job.preview_json?.rows || [];
  const headers = job.preview_json?.headers || [];
  const mutationError = preview.error || confirm.error;
  return <div className="mt-4 space-y-4">
    {mutationError ? <ErrorState error={mutationError} /> : null}
    <fieldset disabled={busy || !editable} className="grid min-w-0 gap-3 sm:grid-cols-2">
      <legend className="mb-3 text-sm font-semibold">{t("integrations.import.columnMapping")}</legend>
      {(job.mapping_fields || []).map(field => <label key={field} className="min-w-0 space-y-1 text-sm">
        <span>{t(`integrations.import.fields.${field}`)}</span>
        <Select aria-label={t(`integrations.import.fields.${field}`)} value={mapping[field] || ""}
          disabled={busy || !editable} data-testid={`import-mapping-${field}`}
          options={[{ value: "", label: t("integrations.import.skipColumn") }, ...headers.map(value => ({ value, label: value }))]}
          onChange={event => { const next = { ...mapping }; if (event.target.value) next[field] = event.target.value; else delete next[field]; setMapping(next); }} />
      </label>)}
    </fieldset>
    {dirty ? <StatusNotice tone="warning" title={t("integrations.import.recheckRequired")} /> : null}
    {editable ? <div className="flex flex-wrap gap-2">
      <Button type="button" variant="secondary" data-testid="import-repreview" disabled={busy || !Object.keys(mapping).length}
        isLoading={preview.isPending} onClick={() => preview.mutate()}>{t("integrations.import.preview")}</Button>
      <Button type="button" data-testid="import-confirm" isLoading={confirm.isPending}
        disabled={!canConfirmImport(job, mapping, busy, Boolean(mutationError))} onClick={() => confirm.mutate()}>{t("integrations.import.confirm")}</Button>
    </div> : null}
    {errors ? <ImportErrors key={`${job.id}:${job.updated_at}`} job={job} userId={userId} /> : null}
    <div className="space-y-2">
      <p className="text-sm font-semibold">{t("integrations.import.previewSample", { shown: rows.length, total: job.total_rows })}</p>
      {rows.length ? <div className="max-h-80 overflow-auto rounded-card border border-platforma-border" tabIndex={0} aria-label={t("integrations.import.preview")}>
        <table className="w-full text-left text-xs"><thead><tr>{headers.map(header => <th key={header} className="whitespace-nowrap p-2">{header}</th>)}</tr></thead>
          <tbody>{rows.map((row, index) => <tr key={index} className="border-t border-platforma-border">{headers.map(header => <td key={header} className="max-w-64 break-words p-2">{row[header] || "—"}</td>)}</tr>)}</tbody>
        </table>
      </div> : <p className="text-sm text-platforma-muted">{t("integrations.import.previewAfterCheck")}</p>}
    </div>
  </div>;
}

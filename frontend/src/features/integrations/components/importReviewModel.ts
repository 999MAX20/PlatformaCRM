import type { ImportJob } from "../../../types";

export function sameImportMapping(left: Record<string, string>, right: Record<string, string>) {
  const entries = Object.entries(left).filter(([, value]) => value);
  return entries.length === Object.entries(right).filter(([, value]) => value).length
    && entries.every(([key, value]) => right[key] === value);
}

export function canConfirmImport(job: ImportJob, mapping: Record<string, string>, busy: boolean, failed: boolean) {
  return job.status === "previewed" && !busy && !failed
    && sameImportMapping(mapping, job.mapping_json)
    && (job.summary_json || job.preview_json?.import_summary)?.ready === true
    && !(job.errors_json?.count ?? job.errors_json?.rows?.length ?? 0);
}

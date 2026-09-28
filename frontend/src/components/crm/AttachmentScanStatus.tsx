import { useI18n } from "../../lib/i18n";
import type { FileAttachment } from "../../types";

const labels = {
  pending: "files.scan.pending",
  scanning: "files.scan.scanning",
  clean: "files.scan.clean",
  infected: "files.scan.infected",
  error: "files.scan.error",
} as const;

export function AttachmentScanStatus({ attachment }: { attachment: FileAttachment }) {
  const { t } = useI18n();
  const state = attachment.scan_status || "pending";
  return <p role="status" data-testid="attachment-scan-status" data-scan-status={state}
    className="mt-1 text-xs font-semibold text-platforma-muted">{t(labels[state] || labels.pending)}</p>;
}

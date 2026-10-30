import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Download, ExternalLink, FilePenLine, FileText, Image, MoreHorizontal, Paperclip, Share2, Upload, X, ZoomIn, ZoomOut } from "lucide-react";
import { useEffect, useState } from "react";
import { getApiErrorMessage } from "../../../api/client";
import { fileAttachmentsApi } from "../../../api/fileAttachments";
import { formatDateTime } from "../../../lib/format";
import { useI18n } from "../../../lib/i18n";
import type { CrmCardPayload, FileAttachment } from "../../../types";
import { Button } from "../../ui/Button";
import { Input } from "../../ui/Input";
import { Dialog, PopoverSurface } from "../../ui/Overlay";
import { ErrorState } from "../../ui/StateViews";
import { AttachmentFilePicker } from "./AttachmentFilePicker";
import { drawerSurfaceClass } from "./shared";
import type { CrmDrawerEntity } from "./types";
import { AttachmentScanStatus } from "../AttachmentScanStatus";

const attachmentAccept = "image/*,.pdf,.doc,.docx,.xls,.xlsx,.csv,.txt";

function formatAttachmentSize(size: number) {
  if (size >= 1024 * 1024) return `${(size / (1024 * 1024)).toFixed(size >= 10 * 1024 * 1024 ? 0 : 1)} MB`;
  return `${Math.max(1, Math.round(size / 1024))} KB`;
}

function isPreviewableAttachment(attachment: FileAttachment) {
  return attachment.scan_status === "clean" && (attachment.content_type.startsWith("image/") || attachment.content_type === "application/pdf" || attachment.content_type.startsWith("text/"));
}

function attachmentTypeLabel(attachment: FileAttachment) {
  if (attachment.content_type.startsWith("image/")) return "Image";
  if (attachment.content_type === "application/pdf") return "PDF";
  if (attachment.content_type.includes("spreadsheet") || attachment.original_name.match(/\.(xls|xlsx|csv)$/i)) return "Spreadsheet";
  if (attachment.content_type.includes("word") || attachment.original_name.match(/\.(doc|docx)$/i)) return "Document";
  if (attachment.content_type.startsWith("text/")) return "Text";
  return attachment.content_type || "File";
}

export function EntityAttachmentsPanel({ data, entity }: { data: CrmCardPayload; entity: CrmDrawerEntity }) {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const awaitingScan = data.attachments.some((item) => !["clean", "infected"].includes(item.scan_status));
  useEffect(() => {
    if (!awaitingScan) return;
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") {
        queryClient.invalidateQueries({ queryKey: ["crm-card", entity.type, entity.id] });
      }
    }, 10000);
    return () => window.clearInterval(timer);
  }, [awaitingScan, queryClient, entity.type, entity.id]);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [previewAttachment, setPreviewAttachment] = useState<FileAttachment | null>(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [previewScale, setPreviewScale] = useState(1);
  const [attachmentActionError, setAttachmentActionError] = useState("");
  const [loadingAttachmentId, setLoadingAttachmentId] = useState<string | number | null>(null);
  const [openAttachmentMenuId, setOpenAttachmentMenuId] = useState<string | number | null>(null);
  const [renamingAttachment, setRenamingAttachment] = useState<FileAttachment | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const businessId = data.client?.business || data.lead?.business || data.deal?.business || data.appointment?.business;
  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!businessId) throw new Error("Business is required.");
      if (!selectedFiles.length) throw new Error("File is required.");
      return Promise.all(
        selectedFiles.map((file) =>
          fileAttachmentsApi.upload({
            business: businessId,
            entityType: entity.type,
            entityId: entity.id,
            file,
          }),
        ),
      );
    },
    onSuccess: async () => {
      setSelectedFiles([]);
      setIsUploadOpen(false);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["crm-card", entity.type, entity.id] }),
        queryClient.invalidateQueries({ queryKey: ["file-attachments"] }),
      ]);
    },
  });
  const renameMutation = useMutation({
    mutationFn: () => {
      if (!renamingAttachment) throw new Error("Attachment is required.");
      return fileAttachmentsApi.rename({ id: renamingAttachment.id, originalName: renameValue.trim() });
    },
    onSuccess: async () => {
      setRenamingAttachment(null);
      setRenameValue("");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["crm-card", entity.type, entity.id] }),
        queryClient.invalidateQueries({ queryKey: ["file-attachments"] }),
      ]);
    },
  });

  function appendFiles(files: FileList | File[]) {
    const nextFiles = Array.from(files);
    if (!nextFiles.length) return;
    setAttachmentActionError("");
    setSelectedFiles((current) => {
      const seen = new Set(current.map((file) => `${file.name}-${file.size}-${file.lastModified}`));
      const unique = nextFiles.filter((file) => {
        const key = `${file.name}-${file.size}-${file.lastModified}`;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      });
      return [...current, ...unique].slice(0, 10);
    });
  }

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  async function loadAttachmentBlob(attachment: FileAttachment) {
    if (attachment.scan_status !== "clean") return null;
    setAttachmentActionError("");
    setLoadingAttachmentId(attachment.id);
    try {
      return await fileAttachmentsApi.downloadBlob(attachment.id);
    } catch (error) {
      setAttachmentActionError(getApiErrorMessage(error));
      return null;
    } finally {
      setLoadingAttachmentId(null);
    }
  }

  async function openAttachmentPreview(attachment: FileAttachment) {
    if (!isPreviewableAttachment(attachment)) return;
    const blob = await loadAttachmentBlob(attachment);
    if (!blob) return;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(URL.createObjectURL(blob));
    setPreviewAttachment(attachment);
    setPreviewScale(1);
  }

  async function downloadAttachment(attachment: FileAttachment) {
    const blob = await loadAttachmentBlob(attachment);
    if (!blob) return;
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = attachment.original_name;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  async function shareAttachment(attachment: FileAttachment) {
    const blob = await loadAttachmentBlob(attachment);
    if (!blob) return;
    const file = new File([blob], attachment.original_name, { type: attachment.content_type || blob.type });
    const navigatorWithShare = navigator as Navigator & {
      canShare?: (data: ShareData & { files?: File[] }) => boolean;
      share?: (data: ShareData & { files?: File[] }) => Promise<void>;
    };
    try {
      if (navigatorWithShare.share && (!navigatorWithShare.canShare || navigatorWithShare.canShare({ files: [file] }))) {
        await navigatorWithShare.share({ title: attachment.original_name, files: [file] });
        return;
      }
      setAttachmentActionError(t("crmCard.shareUnsupported"));
    } catch (error) {
      setAttachmentActionError(getApiErrorMessage(error));
    }
  }

  return (
    <div className={drawerSurfaceClass}>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.12em] text-platforma-faint">
            <Paperclip size={14} /> {t("crmCard.attachments")}
          </div>
          <p className="mt-1 text-sm font-semibold text-platforma-muted">{t("crmCard.attachmentsText")}</p>
        </div>
      </div>
      {data.attachments.length || selectedFiles.length ? (
        <div className="mb-4 flex flex-wrap justify-center gap-2">
          {data.attachments.length ? (
            <Button type="button" variant="secondary" onClick={() => setIsUploadOpen((current) => !current)}>
              <Upload size={16} />
              {isUploadOpen ? t("common.cancel") : t("crmCard.addAttachment")}
            </Button>
          ) : null}
          {selectedFiles.length ? (
            <Button type="button" variant="secondary" isLoading={uploadMutation.isPending} onClick={() => uploadMutation.mutate()}>
              <Upload size={16} />
              {t("crmCard.uploadSelected", { count: selectedFiles.length })}
            </Button>
          ) : null}
        </div>
      ) : null}
      {!data.attachments.length || isUploadOpen || selectedFiles.length ? (
        <AttachmentFilePicker
          accept={attachmentAccept}
          onFiles={appendFiles}
        />
      ) : null}
      {selectedFiles.length ? (
        <div className="mb-4 space-y-2">
          {selectedFiles.map((file) => (
            <div key={`${file.name}-${file.size}-${file.lastModified}`} className="flex items-center justify-between gap-3 rounded-control border border-platforma-border bg-surface-card px-3 py-2">
              <span className="flex min-w-0 items-center gap-2 text-sm font-semibold text-platforma-ink">
                {file.type.startsWith("image/") ? <Image size={15} className="shrink-0 text-brand-600" /> : <FileText size={15} className="shrink-0 text-platforma-muted" />}
                <span className="truncate">{file.name}</span>
              </span>
              <span className="flex shrink-0 items-center gap-2 text-xs font-semibold text-platforma-muted">
                {formatAttachmentSize(file.size)}
                <button
                  type="button"
                  className="grid h-7 w-7 place-items-center rounded-md text-platforma-faint transition hover:bg-[var(--platforma-danger-soft)] hover:text-platforma-danger"
                  onClick={() => setSelectedFiles((current) => current.filter((item) => item !== file))}
                  aria-label={t("crmCard.removeFile")}
                >
                  <X size={14} />
                </button>
              </span>
            </div>
          ))}
        </div>
      ) : null}
      {uploadMutation.error || attachmentActionError ? (
        <div className="mb-4">
          <ErrorState message={uploadMutation.error ? getApiErrorMessage(uploadMutation.error) : attachmentActionError} />
        </div>
      ) : null}
      {data.attachments.length ? (
        <div className="space-y-2">
          {data.attachments.map((attachment) => (
            <div
              key={attachment.id}
              className="relative flex min-w-0 items-center justify-between gap-3 rounded-card border border-platforma-border bg-surface-muted px-3 py-2.5 transition hover:border-brand-200 hover:bg-surface-card"
            >
              <div className="flex min-w-0 items-center gap-3">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-control bg-surface-card text-brand-600 shadow-xs">
                  {attachment.content_type.startsWith("image/") ? <Image size={18} /> : <FileText size={18} />}
                </span>
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-platforma-ink">{attachment.original_name}</p>
                  <p className="mt-0.5 truncate text-xs font-semibold text-platforma-muted">
                    {attachmentTypeLabel(attachment)} · {formatAttachmentSize(attachment.size)} · {formatDateTime(attachment.created_at)}
                  </p>
                  <AttachmentScanStatus attachment={attachment} />
                </div>
              </div>
              <button
                type="button"
                className="grid h-9 w-9 shrink-0 place-items-center rounded-control border border-platforma-border bg-surface-card text-platforma-muted shadow-xs transition hover:bg-surface-hover hover:text-platforma-ink"
                onClick={() => setOpenAttachmentMenuId((current) => (current === attachment.id ? null : attachment.id))}
                aria-label={t("crmCard.fileActions")}
              >
                <MoreHorizontal size={18} />
              </button>
              {openAttachmentMenuId === attachment.id ? (
                <>
                  <button type="button" className="fixed inset-0 z-[9] cursor-default" aria-label={t("common.close")} onClick={() => setOpenAttachmentMenuId(null)} />
                  <PopoverSurface className="absolute right-3 top-12 z-10 w-48 p-1">
                    <button
                      type="button"
                      className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm font-semibold text-platforma-text transition hover:bg-surface-hover disabled:cursor-not-allowed disabled:bg-disabled-surface disabled:text-disabled-content disabled:ring-1 disabled:ring-disabled-border disabled:opacity-100"
                      disabled={!isPreviewableAttachment(attachment)}
                      onClick={() => {
                        setOpenAttachmentMenuId(null);
                        openAttachmentPreview(attachment);
                      }}
                    >
                      <ExternalLink size={15} />
                      {t("crmCard.previewFile")}
                    </button>
                    <button
                      type="button"
                      className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm font-semibold text-platforma-text transition hover:bg-surface-hover"
                      onClick={() => {
                        renameMutation.reset();
                        setOpenAttachmentMenuId(null);
                        setRenamingAttachment(attachment);
                        setRenameValue(attachment.original_name);
                      }}
                    >
                      <FilePenLine size={15} />
                      {t("crmCard.renameFile")}
                    </button>
                    <button
                      type="button"
                      disabled={attachment.scan_status !== "clean"}
                      className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm font-semibold text-platforma-text transition hover:bg-surface-hover"
                      onClick={() => {
                        setOpenAttachmentMenuId(null);
                        downloadAttachment(attachment);
                      }}
                    >
                      <Download size={15} />
                      {loadingAttachmentId === attachment.id ? t("common.loading") : t("crmCard.downloadFile")}
                    </button>
                    <button
                      type="button"
                      disabled={attachment.scan_status !== "clean"}
                      className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm font-semibold text-platforma-text transition hover:bg-surface-hover"
                      onClick={() => {
                        setOpenAttachmentMenuId(null);
                        shareAttachment(attachment);
                      }}
                    >
                      <Share2 size={15} />
                      {loadingAttachmentId === attachment.id ? t("common.loading") : t("crmCard.shareFile")}
                    </button>
                  </PopoverSurface>
                </>
              ) : null}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm leading-6 text-platforma-muted">{t("crmCard.noAttachments")}</p>
      )}
      <Dialog
        title={previewAttachment?.original_name || t("crmCard.previewFile")}
        open={Boolean(previewAttachment && previewUrl)}
        size="xl"
        className="max-w-[min(96vw,1440px)]"
        bodyClassName="flex min-h-0 flex-col gap-4"
        onClose={() => {
          setPreviewAttachment(null);
          if (previewUrl) URL.revokeObjectURL(previewUrl);
          setPreviewUrl("");
          setPreviewScale(1);
        }}
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="text-sm font-semibold text-platforma-muted">
            {previewAttachment ? `${attachmentTypeLabel(previewAttachment)} · ${formatAttachmentSize(previewAttachment.size)}` : null}
          </div>
          <div className="flex items-center gap-2">
            <Button type="button" variant="secondary" size="sm" onClick={() => setPreviewScale((value) => Math.max(0.5, Number((value - 0.25).toFixed(2))))} aria-label={t("crmCard.zoomOut")}>
              <ZoomOut size={15} />
            </Button>
            <button type="button" className="min-h-9 rounded-control border border-platforma-border bg-surface-card px-3 text-xs font-semibold text-platforma-subtle" onClick={() => setPreviewScale(1)}>
              {Math.round(previewScale * 100)}%
            </button>
            <Button type="button" variant="secondary" size="sm" onClick={() => setPreviewScale((value) => Math.min(3, Number((value + 0.25).toFixed(2))))} aria-label={t("crmCard.zoomIn")}>
              <ZoomIn size={15} />
            </Button>
          </div>
        </div>
        <div className="min-h-[62vh] overflow-auto rounded-card border border-platforma-border bg-surface-muted p-3">
          {previewAttachment?.content_type.startsWith("image/") ? (
            <div className="flex min-h-[62vh] items-start justify-center">
              <img
                src={previewUrl}
                alt={previewAttachment.original_name}
                className="max-w-none rounded-card bg-surface-card object-contain shadow-xs"
                style={{ width: `${previewScale * 100}%` }}
              />
            </div>
          ) : previewAttachment?.content_type === "application/pdf" || previewAttachment?.content_type.startsWith("text/") ? (
            <iframe
              title={previewAttachment.original_name}
              src={`${previewUrl}#zoom=${Math.round(previewScale * 100)}`}
              className="h-[72vh] w-full rounded-card border border-platforma-border bg-surface-card"
            />
          ) : null}
        </div>
        <div className="flex justify-end">
          <Button type="button" variant="secondary" onClick={() => previewAttachment && downloadAttachment(previewAttachment)}>
            <Download size={16} />
            {t("crmCard.downloadFile")}
          </Button>
        </div>
      </Dialog>
      <Dialog
        title={t("crmCard.renameFile")}
        open={Boolean(renamingAttachment)}
        onClose={() => {
          renameMutation.reset();
          setRenamingAttachment(null);
          setRenameValue("");
        }}
        size="sm"
      >
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            renameMutation.mutate();
          }}
        >
          <Input label={t("crmCard.fileName")} value={renameValue} onChange={(event) => setRenameValue(event.target.value)} required />
          {renameMutation.error ? <ErrorState error={renameMutation.error} message={getApiErrorMessage(renameMutation.error)} /> : null}
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                renameMutation.reset();
                setRenamingAttachment(null);
                setRenameValue("");
              }}
            >
              {t("common.cancel")}
            </Button>
            <Button type="submit" disabled={!renameValue.trim()} isLoading={renameMutation.isPending}>
              {t("crmCard.saveFileName")}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}

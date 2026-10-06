import { Check, Copy } from "lucide-react";
import { useState } from "react";

import type { AppError } from "../../api/appError";
import { cn } from "../../lib/cn";
import { useI18n } from "../../lib/i18n";
import { canShowSupportDetails } from "../actions/actionFeedbackPolicy";

export function RecoveryDetails({ error, className }: { error: AppError; className?: string }) {
  const { t } = useI18n();
  const [copied, setCopied] = useState(false);
  const [copyFailed, setCopyFailed] = useState(false);

  if (!error.requestId) return null;
  if (!canShowSupportDetails(error)) return null;

  return (
    <details
      data-testid="recovery-details"
      className={cn("rounded-control border border-platforma-border bg-surface-card px-3 py-2 text-xs text-platforma-subtle", className)}
    >
      <summary className="platforma-focus-ring cursor-pointer rounded-sm font-semibold text-platforma-text">
        {t("fallback.recovery.summary")}
      </summary>
      <p className="mt-2 leading-5">{t("fallback.recovery.help")}</p>
      <div className="mt-2 flex flex-wrap items-center gap-2 border-t border-platforma-border pt-2">
        <span>{t("fallback.recovery.requestId")}</span>
        <code className="max-w-full select-all break-all rounded bg-surface-muted px-2 py-1 font-mono text-[11px] text-platforma-text">
          {error.requestId}
        </code>
        <button
          type="button"
          className="platforma-focus-ring ml-auto inline-flex min-h-8 items-center gap-1.5 rounded-control px-2 font-semibold text-brand-700 hover:bg-brand-50"
          aria-label={t("fallback.recovery.copy")}
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(error.requestId!);
              setCopied(true);
              setCopyFailed(false);
              window.setTimeout(() => setCopied(false), 2_000);
            } catch {
              setCopied(false);
              setCopyFailed(true);
            }
          }}
        >
          {copied ? <Check aria-hidden="true" size={14} /> : <Copy aria-hidden="true" size={14} />}
          {copied ? t("fallback.recovery.copied") : t("fallback.recovery.copy")}
        </button>
      </div>
      {copyFailed ? <p role="status" className="mt-2">{t("fallback.recovery.copyFailed")}</p> : null}
    </details>
  );
}

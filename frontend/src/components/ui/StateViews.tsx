import { Inbox } from "lucide-react";
import { useMemo } from "react";

import { normalizeAppError, type AppError } from "../../api/appError";
import { cn } from "../../lib/cn";
import { useI18n } from "../../lib/i18n";
import { InlineFallback, PermissionFallback } from "./FallbackSurfaces";
import { LoadingIndicator } from "./LoadingIndicator";

export function LoadingState({ label, scope = "block" }: { label?: string; scope?: "block" | "page" }) {
  const { t } = useI18n();
  const resolvedLabel = label || t("common.loadingData");
  return <LoadingIndicator label={resolvedLabel} scope={scope} />;
}

export function ErrorState({ error, message, action }: { error?: unknown; message?: string; action?: React.ReactNode }) {
  const appError = useMemo(() => normalizeAppError(error), [error]);
  return <InlineFallback error={appError} message={message} action={action} />;
}

export function ForbiddenState({
  error,
  title,
  message,
}: {
  error?: AppError;
  title?: string;
  message?: string;
}) {
  const { t } = useI18n();
  const permissionError: AppError = error || {
    category: "permission", code: "permission_denied", fieldErrors: {},
    messageKey: "actions.errorForbidden", retryable: false,
    retryPolicy: "never_blindly", source: "runtime",
  };
  return <PermissionFallback error={permissionError}
    testId={error ? "permission-fallback" : "forbidden-state"}
    title={title || t("permissions.hiddenTitle")} message={message}
    guidance={t("permissions.hiddenText")} />;
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="rounded-card border border-dashed border-platforma-border bg-surface-card p-6 text-center shadow-card">
      <div className="mx-auto mb-3 grid h-11 w-11 place-items-center rounded-control bg-surface-muted text-platforma-subtle">
        <Inbox aria-hidden="true" size={22} />
      </div>
      <p className="text-base font-semibold text-platforma-ink">{title}</p>
      {description ? <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-platforma-subtle">{description}</p> : null}
      {action ? <div className="mt-4 flex justify-center">{action}</div> : null}
    </div>
  );
}

export function SkeletonBlock({ className }: { className?: string }) {
  return <div aria-hidden="true" className={cn("animate-pulse rounded-control bg-surface-muted", className)} />;
}

export function PageSkeleton() {
  return <LoadingState scope="page" />;
}

export { ConnectivityBanner } from "./ConnectivityBanner";
export { FieldErrorSummary } from "./FieldErrorSummary";
export { InlineFallback, PageFallback, PermissionFallback } from "./FallbackSurfaces";
export { RecoveryDetails } from "./RecoveryDetails";

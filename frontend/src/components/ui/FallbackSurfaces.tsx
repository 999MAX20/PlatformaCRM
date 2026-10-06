import { RefreshCw, ShieldAlert } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { normalizeAppError, type AppError } from "../../api/appError";
import { useI18n } from "../../lib/i18n";
import { canOfferActionRecovery } from "../actions/actionFeedbackPolicy";
import { useRecoveryDelay } from "../actions/useRecoveryDelay";
import { Button } from "./Button";
import { RecoveryDetails } from "./RecoveryDetails";
import { appErrorNoticeTone, statusNoticeTones, StatusNotice, type StatusNoticeTone } from "./StatusNotice";

type FallbackActionProps = {
  error: AppError;
  onRetry?: () => Promise<void> | void;
};

function FallbackAction({ error, onRetry }: FallbackActionProps) {
  const { t } = useI18n();
  const [isRetrying, setIsRetrying] = useState(false);
  const [retryError, setRetryError] = useState<AppError>();
  const pending = useRef(false);
  useEffect(() => setRetryError(undefined), [error]);
  const currentError = retryError || error;
  const delay = useRecoveryDelay(currentError);

  if (!canOfferActionRecovery(error, Boolean(onRetry)) || !onRetry) return null;

  return (
    <div className="flex flex-col items-center gap-2">
    <Button
      type="button"
      size="sm"
      variant="secondary"
      isLoading={isRetrying}
      disabled={delay > 0 || !canOfferActionRecovery(currentError, true)}
      onClick={async () => {
        if (pending.current || delay > 0) return;
        pending.current = true;
        setIsRetrying(true);
        try {
          await onRetry();
        } catch (cause) {
          setRetryError(normalizeAppError(cause));
        } finally {
          pending.current = false;
          setIsRetrying(false);
        }
      }}
    >
      <RefreshCw aria-hidden="true" size={16} />
      {delay > 0 ? t("fallback.retryAfter", { seconds: delay }) : t("common.retry")}
    </Button>
    {retryError ? <p role="alert" className="max-w-sm text-sm text-platforma-subtle">{t(retryError.messageKey)}</p> : null}
    </div>
  );
}

type SharedFallbackProps = {
  error: AppError;
  onRetry?: () => Promise<void> | void;
  title?: string;
  message?: string;
  action?: ReactNode;
};

const errorTitles: Record<AppError["category"], string> = {
  validation: "fallback.fields.title",
  authentication: "fallback.title.authentication",
  permission: "fallback.permission.title",
  not_found: "fallback.title.notFound",
  conflict: "fallback.title.conflict",
  rate_limit: "fallback.title.rateLimit",
  offline: "fallback.connectivity.offlineTitle",
  temporary: "fallback.title.temporary",
  provider: "fallback.title.provider",
  internal: "fallback.inline.title",
};

export function InlineFallback({ error, onRetry, title, message, action }: SharedFallbackProps) {
  const { t } = useI18n();
  return (
    <StatusNotice
      data-testid="inline-fallback"
      tone={appErrorNoticeTone(error)}
      title={title || t(errorTitles[error.category])}
      description={message || t(error.messageKey)}
      action={action || <FallbackAction error={error} onRetry={onRetry} />}
      details={<RecoveryDetails error={error} />}
    />
  );
}

type PageFallbackProps = SharedFallbackProps & {
  secondaryAction?: ReactNode;
};

type PageFallbackLayoutProps = {
  actions?: ReactNode;
  details?: ReactNode;
  message: string;
  testId?: string;
  title: string;
  tone?: StatusNoticeTone;
};

export function PageFallbackLayout({
  actions,
  details,
  message,
  testId = "page-fallback",
  title,
  tone = "danger",
}: PageFallbackLayoutProps) {
  const toneDefinition = statusNoticeTones[tone];
  const Icon = toneDefinition.Icon;
  return (
    <section
      data-testid={testId}
      role="alert"
      className="grid min-h-[280px] place-items-center rounded-card border border-platforma-border bg-surface-card p-6 shadow-card"
    >
      <div className="w-full max-w-xl text-center">
        <div className={`mx-auto grid h-12 w-12 place-items-center rounded-control border ${toneDefinition.container} ${toneDefinition.icon}`}>
          <Icon aria-hidden="true" size={24} />
        </div>
        <h2 className="mt-4 text-xl font-semibold text-platforma-ink">{title}</h2>
        <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-platforma-subtle">{message}</p>
        {actions ? <div className="mt-5 flex flex-wrap justify-center gap-2">{actions}</div> : null}
        {details}
      </div>
    </section>
  );
}

export function PageFallback({ error, onRetry, secondaryAction, title }: PageFallbackProps) {
  const { t } = useI18n();
  return (
    <PageFallbackLayout
      title={title || t("fallback.page.title")}
      message={t(error.messageKey)}
      tone={appErrorNoticeTone(error)}
      actions={(
        <>
          <FallbackAction error={error} onRetry={onRetry} />
          {secondaryAction}
        </>
      )}
      details={<RecoveryDetails error={error} className="mx-auto mt-4 max-w-md text-left" />}
    />
  );
}

export function PermissionFallback({ error, title, message, guidance, testId = "permission-fallback" }: Pick<SharedFallbackProps, "error" | "title" | "message"> & { guidance?: string; testId?: string }) {
  const { t } = useI18n();
  return (
    <StatusNotice
      data-testid={testId}
      tone="warning"
      icon={ShieldAlert}
      title={title || t("fallback.permission.title")}
      description={message || t(error.messageKey)}
      details={(
        <>
          <p className="rounded-control bg-surface-card px-3 py-2 text-xs font-semibold text-platforma-warning">
            {guidance || t("fallback.permission.guidance")}
          </p>
          <RecoveryDetails error={error} className="mt-3" />
        </>
      )}
    />
  );
}

import { RefreshCw, WifiOff, X } from "lucide-react";

import type { AppError } from "../../api/appError";
import { useI18n } from "../../lib/i18n";
import { canOfferActionRecovery } from "../actions/actionFeedbackPolicy";
import { Button } from "./Button";
import { StatusNotice } from "./StatusNotice";

type ConnectivityBannerProps = {
  error: AppError;
  isReconnecting?: boolean;
  onRetry?: () => Promise<void> | void;
  onDismiss?: () => void;
};

export function ConnectivityBanner({ error, isReconnecting = false, onRetry, onDismiss }: ConnectivityBannerProps) {
  const { t } = useI18n();
  const canRetry = !isReconnecting && canOfferActionRecovery(error, Boolean(onRetry));

  return (
    <StatusNotice
      data-testid="connectivity-banner"
      tone="warning"
      role="status"
      ariaLive="polite"
      compact
      icon={isReconnecting ? RefreshCw : WifiOff}
      iconClassName={isReconnecting ? "animate-spin motion-reduce:animate-none" : undefined}
      title={t(isReconnecting ? "fallback.connectivity.reconnectingTitle" : "fallback.connectivity.offlineTitle")}
      description={t(isReconnecting ? "fallback.connectivity.reconnectingText" : error.messageKey)}
      dismiss={onDismiss ? <button type="button" className="platforma-notice-close" aria-label={t("common.close")} onClick={onDismiss}><X aria-hidden="true" size={16} /></button> : null}
      action={canRetry && onRetry ? (
        <Button type="button" size="sm" variant="secondary" onClick={onRetry}>
          {t("common.retry")}
        </Button>
      ) : null}
    />
  );
}

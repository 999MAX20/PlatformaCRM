import { X } from "lucide-react";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import type { AppError } from "../../api/appError";
import { Button } from "../ui/Button";
import { useI18n } from "../../lib/i18n";
import { StatusNotice, type StatusNoticeTone } from "../ui/StatusNotice";
import { RecoveryDetails } from "../ui/RecoveryDetails";
import { useRecoveryDelay } from "../actions/useRecoveryDelay";
import { canShowSupportDetails } from "../actions/actionFeedbackPolicy";
import { notificationDedupeKey } from "./notificationPolicy";

type NotificationTone = StatusNoticeTone;

export type NotificationOptions = {
  appError?: AppError;
  message?: string;
  tone?: NotificationTone;
  durationMs?: number;
  actionLabel?: string;
  onAction?: () => Promise<void> | void;
  dedupeKey?: string;
};

type NotificationItem = NotificationOptions & {
  id: number;
  createdAt: number;
};

const NotificationContext = createContext<((options: NotificationOptions) => void) | null>(null);

export function ActionFeedbackToast({ item, onDismiss, dismissAfterAction = true }: { item: NotificationItem; onDismiss: (id: number) => void; dismissAfterAction?: boolean }) {
  const { t } = useI18n();
  const [isHovered, setIsHovered] = useState(false);
  const [isActing, setIsActing] = useState(false);
  const [hasFocus, setHasFocus] = useState(false);
  const delay = useRecoveryDelay(item.appError);
  const tone = item.tone || (item.appError ? "danger" : "info");
  const message = item.message || (item.appError ? t(item.appError.messageKey) : t("actions.errorGeneric"));

  useEffect(() => {
    if (isHovered || hasFocus || isActing || delay > 0) return undefined;
    const timer = window.setTimeout(() => onDismiss(item.id), item.durationMs ?? 5_000);
    return () => window.clearTimeout(timer);
  }, [delay, hasFocus, isActing, isHovered, item.durationMs, item.id, onDismiss]);

  return (
    <StatusNotice
      data-testid="action-feedback"
      compact
      actionPlacement="corner"
      tone={tone}
      title={message}
      className="pointer-events-auto w-[min(360px,calc(100vw-2rem))] shadow-panel backdrop-blur transition"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onFocusCapture={() => setHasFocus(true)}
      onBlurCapture={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setHasFocus(false);
      }}
      role={tone === "danger" || tone === "warning" ? "alert" : "status"}
      ariaLive={tone === "danger" || tone === "warning" ? "assertive" : "polite"}
      action={(
        <button
          type="button"
          className="platforma-focus-ring grid h-7 w-7 shrink-0 place-items-center rounded-control text-platforma-faint transition hover:bg-surface-card hover:text-platforma-text"
          aria-label={t("common.close")}
          onClick={() => onDismiss(item.id)}
        >
          <X size={15} />
        </button>
      )}
      details={(item.actionLabel && item.onAction) || (item.appError && canShowSupportDetails(item.appError)) ? (
        <div className="space-y-3">
        {item.appError ? <RecoveryDetails error={item.appError} /> : null}
        {item.actionLabel && item.onAction ? (
        <div className="flex justify-center">
          <Button
            data-testid="action-feedback-action"
            type="button"
            size="sm"
            variant="secondary"
            className="h-8"
            isLoading={isActing}
            disabled={delay > 0}
            onClick={async () => {
              setIsActing(true);
              try {
                await item.onAction?.();
              } catch {
                // The mutation owns the follow-up error notification. Keep the
                // retry control recoverable and avoid an unhandled rejection.
              } finally {
                if (dismissAfterAction) onDismiss(item.id);
                setIsActing(false);
              }
            }}
          >
            {delay > 0 ? t("fallback.retryAfter", { seconds: delay }) : item.actionLabel}
          </Button>
        </div>
        ) : null}
        </div>
      ) : null}
    />
  );
}

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<NotificationItem[]>([]);

  const dismiss = useCallback((id: number) => {
    setItems((current) => current.filter((item) => item.id !== id));
  }, []);

  const showNotification = useCallback((options: NotificationOptions) => {
    setItems((current) => {
      const key = notificationDedupeKey(options);
      if (key && current.some(item => notificationDedupeKey(item) === key)) return current;
      return [
        {
          ...options,
          id: Date.now() + Math.floor(Math.random() * 1000),
          createdAt: Date.now(),
        },
        ...current,
      ].slice(0, 4);
    });
  }, []);

  const value = useMemo(() => showNotification, [showNotification]);

  return (
    <NotificationContext.Provider value={value}>
      {children}
      <div
        className="pointer-events-none fixed bottom-5 right-5 flex max-h-[calc(100dvh-8rem)] flex-col-reverse items-end gap-2 overflow-y-auto"
        style={{ zIndex: "var(--platforma-z-toast)" }}
      >
        {items.map((item) => (
          <ActionFeedbackToast key={item.id} item={item} onDismiss={dismiss} />
        ))}
      </div>
    </NotificationContext.Provider>
  );
}

export function useNotification() {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error("useNotification must be used within NotificationProvider");
  }
  return context;
}

import { X } from "lucide-react";
import { createContext, useCallback, useContext, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";

import type { AppError } from "../../api/appError";
import { Button } from "../ui/Button";
import { useI18n } from "../../lib/i18n";
import { appErrorNoticeTone, StatusNotice, type StatusNoticeTone } from "../ui/StatusNotice";
import { RecoveryDetails } from "../ui/RecoveryDetails";
import { useRecoveryDelay } from "../actions/useRecoveryDelay";
import { canShowSupportDetails } from "../actions/actionFeedbackPolicy";
import { notificationContent, notificationDedupeKey } from "./notificationPolicy";
import { NotificationPortal, restoreNoticeFocus } from "./NotificationHost";
import { NotificationCard } from "./NotificationCard";

type NotificationTone = StatusNoticeTone;

export type NotificationOptions = {
  appError?: AppError;
  message?: string;
  title?: string;
  description?: string;
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
  const [leaving, setLeaving] = useState(false);
  const [ready, setReady] = useState(false);
  const cards = useRef(new Set<HTMLDivElement>());
  const opener = useRef(document.activeElement instanceof HTMLElement ? document.activeElement : null);
  const trackCard = useCallback((node: HTMLDivElement | null) => {
    if (!node) return;
    cards.current.add(node);
    return () => { cards.current.delete(node); };
  }, []);
  const restoreFocus = useCallback(() => {
    for (const node of cards.current) restoreNoticeFocus(node, opener.current);
  }, []);
  const pending = useRef(false);
  const delay = useRecoveryDelay(item.appError);
  const tone = item.tone || (item.appError ? appErrorNoticeTone(item.appError) : "info");
  const content = notificationContent(item, item.appError ? t(item.appError.messageKey) : t("actions.errorGeneric"));
  const dismiss = useCallback(() => {
    restoreFocus();
    setLeaving(true);
  }, [restoreFocus]);
  useLayoutEffect(() => () => restoreFocus(), [restoreFocus]);

  useEffect(() => {
    if (!ready || leaving || isHovered || hasFocus || isActing || delay > 0) return undefined;
    const timer = window.setTimeout(dismiss, item.durationMs ?? (tone === "warning" || tone === "danger" ? 7_000 : 5_000));
    return () => window.clearTimeout(timer);
  }, [ready, delay, hasFocus, isActing, isHovered, leaving, item.durationMs, item.id, dismiss, tone]);

  return (
    <NotificationCard leaving={leaving} order={item.id} onReadyChange={setReady} onExited={() => onDismiss(item.id)}>
    <div ref={trackCard}>
    <StatusNotice
      data-testid="action-feedback"
      compact
      actionPlacement="corner"
      tone={tone}
      title={content.title}
      description={content.description}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onFocusCapture={() => setHasFocus(true)}
      onBlurCapture={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setHasFocus(false);
      }}
      role={tone === "danger" || tone === "warning" ? "alert" : "status"}
      ariaLive={tone === "danger" || tone === "warning" ? "assertive" : "polite"}
      dismiss={(
        <button
          type="button"
          className="platforma-notice-close"
          aria-label={t("common.close")}
          onClick={dismiss}
        >
          <X aria-hidden="true" size={16} />
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
              if (pending.current) return;
              pending.current = true;
              setIsActing(true);
              try {
                await item.onAction?.();
                if (dismissAfterAction) dismiss();
              } catch {
                // The mutation owns the follow-up error notification. Keep the
                // retry control recoverable and avoid an unhandled rejection.
              } finally {
                pending.current = false;
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
    </div>
    </NotificationCard>
  );
}

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const nextId = useRef(0);

  const dismiss = useCallback((id: number) => {
    setItems((current) => current.filter((item) => item.id !== id));
  }, []);

  const showNotification = useCallback((options: NotificationOptions) => {
    const item = { ...options, id: ++nextId.current, createdAt: Date.now() };
    setItems((current) => {
      const key = notificationDedupeKey(options);
      if (key && current.some(item => notificationDedupeKey(item) === key)) return current;
      return [...current, item];
    });
  }, []);

  const value = useMemo(() => showNotification, [showNotification]);

  return (
    <NotificationContext.Provider value={value}>
      {children}
      <NotificationPortal group="notifications">
        {/* Pending notices mount only when a slot opens, starting their full reading interval. */}
        {items.slice(0, 4).map((item) => (
          <ActionFeedbackToast key={item.id} item={item} onDismiss={dismiss} />
        ))}
      </NotificationPortal>
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

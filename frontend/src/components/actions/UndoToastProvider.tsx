import { createContext, useCallback, useContext, useRef, useState } from "react";

import { normalizeAppError, type AppError } from "../../api/appError";
import { useI18n } from "../../lib/i18n";
import { ActionFeedbackToast } from "../notifications/NotificationProvider";

type UndoToastOptions = {
  message: string;
  undoLabel?: string;
  durationMs?: number;
  onUndo: () => Promise<void> | void;
  onRecover?: () => Promise<void> | void;
};
type UndoToastItem = UndoToastOptions & { id: number; error?: AppError };
const UndoToastContext = createContext<((options: UndoToastOptions) => void) | null>(null);

export function UndoToastProvider({ children }: { children: React.ReactNode }) {
  const { t } = useI18n();
  const [item, setItem] = useState<UndoToastItem | null>(null);
  const nextId = useRef(0);
  const pendingId = useRef<number | null>(null);
  const showUndoToast = useCallback((options: UndoToastOptions) => {
    setItem({ ...options, id: ++nextId.current });
  }, []);
  const dismiss = useCallback((id: number) => {
    setItem(current => current?.id === id ? null : current);
  }, []);

  async function perform(current: UndoToastItem) {
    if (pendingId.current === current.id) return;
    pendingId.current = current.id;
    try {
      if (current.error) await current.onRecover?.();
      else await current.onUndo();
      dismiss(current.id);
    } catch (error) {
      setItem(latest => latest?.id === current.id ? { ...latest, error: normalizeAppError(error) } : latest);
    } finally {
      if (pendingId.current === current.id) pendingId.current = null;
    }
  }

  return <UndoToastContext.Provider value={showUndoToast}>
    {children}
    {item ? <div className="fixed bottom-5 right-5" style={{ zIndex: "var(--platforma-z-toast)" }}>
      <ActionFeedbackToast key={item.id} dismissAfterAction={false} onDismiss={dismiss} item={{
        id: item.id, createdAt: item.id,
        message: item.error ? t("fallback.undoFailed") : item.message,
        appError: item.error, tone: item.error ? "warning" : "success",
        durationMs: item.error ? 20_000 : item.durationMs ?? 10_000,
        actionLabel: item.error ? (item.onRecover ? t("common.refresh") : undefined) : item.undoLabel || t("actions.undo"),
        onAction: !item.error || item.onRecover ? () => perform(item) : undefined,
      }} />
    </div> : null}
  </UndoToastContext.Provider>;
}

export function useUndoToast() {
  const context = useContext(UndoToastContext);
  if (!context) throw new Error("useUndoToast must be used within UndoToastProvider");
  return context;
}

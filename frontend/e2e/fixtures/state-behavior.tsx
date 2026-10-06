import { useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { normalizeAppError, type AppError } from "../../src/api/appError";
import { UndoToastProvider, useUndoToast } from "../../src/components/actions/UndoToastProvider";
import { NotificationProvider, useNotification } from "../../src/components/notifications/NotificationProvider";
import { Button } from "../../src/components/ui/Button";
import { ConnectivityStatus } from "../../src/components/ui/ConnectivityStatus";
import { ErrorState, InlineFallback, PermissionFallback } from "../../src/components/ui/StateViews";
import { I18nProvider, useI18n } from "../../src/lib/i18n";
import "../../src/styles.css";

const serverError = (code: string, status: number, requestId = "test-reference", delay?: number) => normalizeAppError({
  isAxiosError: true, response: { status, data: { code, detail: "SQLSTATE never-render", request_id: requestId, retry_after_seconds: delay, retryable: status === 429 || status === 503 } },
});
const internalError = { isAxiosError: true, response: { status: 500, data: { code: "internal_error", request_id: "test-internal", detail: "SQLSTATE never-render" } } };
const permission = serverError("permission_denied", 403);
const temporary = serverError("temporary_service_failure", 503);

function Fixture() {
  const { t } = useI18n();
  const notify = useNotification();
  const undo = useUndoToast();
  const [rate, setRate] = useState<AppError | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [undoCount, setUndoCount] = useState(0);
  const [recoveryCount, setRecoveryCount] = useState(0);
  const finishOld = useRef<() => void>(() => undefined);
  const reads = useRef(0);
  const query = useQuery({ queryKey: ["fixture-read"], queryFn: async () => ++reads.current, staleTime: Infinity });
  return <>
    <ConnectivityStatus />
    <main className="mx-auto max-w-3xl space-y-4 p-4">
      <input data-testid="draft" aria-label="Draft" defaultValue="Keep my draft" />
      <output data-testid="counts">{retryCount},{undoCount},{recoveryCount}</output>
      <output data-testid="reads">{query.data}</output>
      <div className="flex flex-wrap gap-3">
        <Button data-testid="duplicate" onClick={() => { notify({ appError: temporary }); notify({ appError: temporary }); }}>{t("common.open")}</Button>
        <Button data-testid="short-toast" onClick={() => notify({ message: t("common.saved"), durationMs: 1000 })}>{t("common.saved")}</Button>
        <Button data-testid="rate" onClick={() => setRate(serverError("rate_limited", 429, "rate-test", 2))}>{t("common.retry")}</Button>
        <Button data-testid="rate-toast" onClick={() => notify({ appError: serverError("rate_limited", 429, "rate-toast", 2), durationMs: 1000, actionLabel: t("common.retry"), onAction: () => setRetryCount(n => n + 1) })}>{t("common.retry")}</Button>
        <Button data-testid="undo-failure" onClick={() => undo({ message: t("clients.noticeArchived"), onUndo: async () => { setUndoCount(n => n + 1); throw internalError; }, onRecover: () => setRecoveryCount(n => n + 1) })}>{t("actions.undo")}</Button>
        <Button data-testid="undo-pending" onClick={() => undo({ message: "Old operation", onUndo: () => new Promise<void>(resolve => { finishOld.current = resolve; }) })}>Old</Button>
        <Button data-testid="undo-new" onClick={() => undo({ message: "New operation", onUndo: () => undefined })}>New</Button>
        <Button data-testid="finish-old" onClick={() => finishOld.current()}>Finish</Button>
      </div>
      {rate ? <InlineFallback error={rate} onRetry={() => { setRetryCount(n => n + 1); setRate(null); }} /> : null}
      <section data-testid="support-case"><ErrorState error={internalError} /></section>
      <section data-testid="permission-case"><PermissionFallback error={permission} /></section>
    </main>
  </>;
}
const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnReconnect: false } } });
createRoot(document.getElementById("root")!).render(<I18nProvider><QueryClientProvider client={queryClient}><NotificationProvider><UndoToastProvider><Fixture /></UndoToastProvider></NotificationProvider></QueryClientProvider></I18nProvider>);

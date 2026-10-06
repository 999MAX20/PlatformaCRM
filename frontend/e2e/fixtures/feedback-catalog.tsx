import { useState, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter } from "react-router";
import { AlertTriangle } from "lucide-react";

import { normalizeAppError, type AppError } from "../../src/api/appError";
import { ActionFeedbackToast } from "../../src/components/notifications/NotificationProvider";
import { UnreadMessagesNotice } from "../../src/components/notifications/UnreadMessagesNotice";
import { UndoToastProvider, useUndoToast } from "../../src/components/actions/UndoToastProvider";
import { AiInsightCard } from "../../src/components/ai/AiInsightCard";
import { AppErrorBoundary } from "../../src/components/ui/AppErrorBoundary";
import { Button } from "../../src/components/ui/Button";
import { Input } from "../../src/components/ui/Input";
import { RouteErrorView } from "../../src/components/ui/RouteErrorBoundary";
import { StatusNotice } from "../../src/components/ui/StatusNotice";
import { ConnectivityBanner, EmptyState, ErrorState, FieldErrorSummary, InlineFallback, LoadingState, PageFallback, PageSkeleton, PermissionFallback } from "../../src/components/ui/StateViews";
import { I18nProvider, useI18n } from "../../src/lib/i18n";
import "@fontsource-variable/manrope";
import "@fontsource-variable/noto-sans";
import "../../src/styles.css";

// Development evidence only: the catalog renders production components and copy.
const errorInputs = [
  ["validation", 400, "validation_error"], ["authentication", 401, "authentication_required"], ["permission", 403, "permission_denied"],
  ["not_found", 404, "not_found"], ["conflict", 409, "request_conflict"], ["rate_limit", 429, "rate_limited"],
  ["temporary", 503, "temporary_service_failure"], ["internal", 500, "internal_error"], ["provider", 503, "provider_unavailable"],
] as const;
const errors: Record<string, AppError> = Object.fromEntries(errorInputs.map(([name, status, code]) => [name, normalizeAppError({
  isAxiosError: true, response: { status, data: { code, detail: "SQLSTATE never-render", request_id: `example-${name}`, retryable: status === 503 || status === 429, retry_after_seconds: status === 429 ? 5 : undefined } },
})]));
errors.offline = normalizeAppError({ isAxiosError: true, message: "Network Error" });

function Crash(): never { throw new Error("SQLSTATE never-render"); }

function UndoExample() {
  const showUndo = useUndoToast();
  const { t } = useI18n();
  return <Button data-testid="show-undo" onClick={() => showUndo({ message: t("clients.noticeArchived"), durationMs: 3_600_000, onUndo: () => undefined })}>{t("actions.undo")}</Button>;
}

function Catalog() {
  const { t, language } = useI18n();
  const [recovered, setRecovered] = useState(0);
  const [dismissed, setDismissed] = useState(false);
  const recover = () => setRecovered((count) => count + 1);
  const action = <Button onClick={recover}>{t("common.retry")}</Button>;
  const cases: [string, ReactNode][] = [
    ["session-recovery", <ErrorState error={{ isAxiosError: true, response: { status: 503, data: { code: "temporary_service_failure", request_id: "example-session", retryable: true } } }} action={action} />],
    ...Object.entries(errors).filter(([name]) => !["permission", "offline"].includes(name)).map(([name, error]): [string, ReactNode] => [`inline-${name}`, <InlineFallback error={error} onRetry={recover} />]),
    ["page-error", <PageFallback error={errors.temporary} onRetry={recover} secondaryAction={<Button variant="ghost" onClick={recover}>{t("routeError.home")}</Button>} />],
    ["permission", <PermissionFallback error={errors.permission} />],
    ["offline", <ConnectivityBanner error={errors.offline} onRetry={recover} />],
    ["reconnecting", <ConnectivityBanner error={errors.offline} isReconnecting />],
    ["validation", <FieldErrorSummary error={{ ...errors.validation, fieldErrors: { email: ["SQLSTATE private technical message"] } }} fieldLabels={{ email: t("common.email") }} onFieldSelect={recover} />],
    ["empty", <EmptyState title={t("payments.empty")} description={t("payments.emptyText")} action={<Button onClick={recover}>{t("payments.add")}</Button>} />],
    ["loading", <LoadingState />],
    ["field", <Input label={t("common.email")} error={t("fallback.fields.invalidValue")} />],
    ["toast-success", dismissed ? null : <ActionFeedbackToast item={{ id: 1, createdAt: 0, tone: "success", message: t("payments.saved"), durationMs: 3_600_000 }} onDismiss={() => setDismissed(true)} />],
    ["toast-danger", dismissed ? null : <ActionFeedbackToast item={{ id: 2, createdAt: 0, tone: "danger", appError: errors.temporary, durationMs: 3_600_000, actionLabel: t("common.retry"), onAction: recover }} onDismiss={() => setDismissed(true)} />],
    ["route-error", <RouteErrorView error={new Error("SQLSTATE never-render")} onBack={recover} onHome={recover} />],
    ["payment-uncertain", <StatusNotice tone="warning" title={t("payments.uncertain")} description={t("payments.uncertainClose")} action={action} />],
    ["ai-unavailable", <StatusNotice tone="warning" title={t("aiQuality.unavailable")} action={action} />],
    ["unread-messages", <UnreadMessagesNotice count={5} onOpen={recover} onDismiss={recover} />],
    ["page-loading", <PageSkeleton />],
    ["app-crash", <AppErrorBoundary><Crash /></AppErrorBoundary>],
    ["undo", <UndoToastProvider><UndoExample /></UndoToastProvider>],
    ["ai-insight", <AiInsightCard icon={AlertTriangle} severity="warning" title={t("dashboard.overdueTasks")} description={t("dashboard.overdueTasksCount", { count: 3 })} actionLabel={t("common.open")} href="/app/tasks" />],
  ];
  const selected = new URLSearchParams(location.search).get("case");
  return <main data-language={language} className="min-h-screen bg-platforma-bg p-4 text-platforma-text sm:p-6">
    <output data-testid="recovered" className="sr-only">{recovered}</output>
    <div className="mx-auto max-w-3xl space-y-6">
      {cases.filter(([name]) => !selected || name === selected).map(([name, component]) => <section key={name} data-catalog-case={name}>
        <h1 className="mb-3 text-sm font-semibold">{name}</h1>
        {component}
      </section>)}
    </div>
  </main>;
}

createRoot(document.getElementById("root")!).render(<MemoryRouter><I18nProvider><Catalog /></I18nProvider></MemoryRouter>);

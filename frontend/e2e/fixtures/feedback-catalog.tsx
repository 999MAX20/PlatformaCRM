import { useState, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { AlertTriangle } from "lucide-react";

import { normalizeAppError, type AppError } from "../../src/api/appError";
import { ActionFeedbackToast } from "../../src/components/notifications/NotificationProvider";
import { UnreadMessagesNotice } from "../../src/components/notifications/UnreadMessagesNotice";
import { UndoToastProvider, useUndoToast } from "../../src/components/actions/UndoToastProvider";
import { AiInsightCard } from "../../src/components/ai/AiInsightCard";
import { AppErrorBoundary } from "../../src/components/ui/AppErrorBoundary";
import { Badge } from "../../src/components/ui/Badge";
import { Button } from "../../src/components/ui/Button";
import { Card } from "../../src/components/ui/Card";
import { Input } from "../../src/components/ui/Input";
import { RouteErrorView } from "../../src/components/ui/RouteErrorBoundary";
import { StatusNotice, type StatusNoticeTone } from "../../src/components/ui/StatusNotice";
import { ConnectivityBanner, EmptyState, ErrorState, FieldErrorSummary, ForbiddenState, InlineFallback, LoadingState, PageFallback, PageSkeleton, PermissionFallback } from "../../src/components/ui/StateViews";
import { I18nProvider, useI18n } from "../../src/lib/i18n";
import "@fontsource-variable/manrope";
import "@fontsource-variable/noto-sans";
import "../../src/styles.css";

// Development evidence only: the catalog renders production components and copy.
const errorInputs = [
  ["validation", 400], ["authentication", 401], ["permission", 403],
  ["not_found", 404], ["conflict", 409], ["rate_limit", 429],
  ["temporary", 503], ["internal", 500],
] as const;
const errors: Record<string, AppError> = Object.fromEntries(errorInputs.map(([name, status]) => [name, normalizeAppError({
  isAxiosError: true, response: { status, data: { detail: "SQLSTATE never-render", request_id: "catalog-reference", retryable: status === 503 || status === 429 } },
})]));
errors.offline = normalizeAppError({ isAxiosError: true, message: "Network Error" });
errors.provider = { ...errors.temporary, category: "provider", retryPolicy: "owned_status_surface_only" };

function Crash(): never { throw new Error("SQLSTATE never-render"); }

function UndoExample() {
  const showUndo = useUndoToast();
  const { t } = useI18n();
  return <Button data-testid="show-undo" onClick={() => showUndo({ message: t("payments.saved"), durationMs: 3_600_000, onUndo: () => undefined })}>{t("actions.undo")}</Button>;
}

function Catalog() {
  const { t, language } = useI18n();
  const [recovered, setRecovered] = useState(0);
  const [dismissed, setDismissed] = useState(false);
  const recover = () => setRecovered((count) => count + 1);
  const action = <Button onClick={recover}>{t("common.retry")}</Button>;
  const tones: StatusNoticeTone[] = ["success", "info", "warning", "danger"];
  const cases: [string, ReactNode][] = [
    ["session-recovery", <ErrorState message={t(errors.temporary.messageKey)} action={action} />],
    ...tones.map((tone): [string, ReactNode] => [`notice-${tone}`, <StatusNotice tone={tone} title={t(tone === "success" ? "payments.saved" : "fallback.inline.title")} description={tone === "success" ? undefined : t(errors.temporary.messageKey)} action={tone === "success" ? undefined : action} />]),
    ...Object.entries(errors).map(([name, error]): [string, ReactNode] => [`inline-${name}`, <InlineFallback error={error} onRetry={recover} />]),
    ["page-error", <PageFallback error={errors.temporary} onRetry={recover} secondaryAction={<Button variant="ghost" onClick={recover}>{t("routeError.home")}</Button>} />],
    ["permission", <PermissionFallback error={errors.permission} />],
    ["offline", <ConnectivityBanner error={errors.offline} onRetry={recover} />],
    ["reconnecting", <ConnectivityBanner error={errors.offline} isReconnecting />],
    ["validation", <FieldErrorSummary error={{ ...errors.validation, fieldErrors: { email: ["SQLSTATE private technical message"] } }} fieldLabels={{ email: t("common.email") }} onFieldSelect={recover} />],
    ["empty", <EmptyState title={t("payments.empty")} description={t("payments.emptyText")} action={action} />],
    ["loading", <LoadingState />],
    ["field", <Input label={t("common.email")} error={t("fallback.fields.invalidValue")} />],
    ["danger-card", <Card variant="danger" padding="md">{t("actions.errorGeneric")}</Card>],
    ...tones.map((tone): [string, ReactNode] => [`badge-${tone}`, <Badge variant={tone}>{t(tone === "success" ? "payments.saved" : "actions.errorGeneric")}</Badge>]),
    ...tones.map((tone, id): [string, ReactNode] => [`toast-${tone}`, dismissed ? null : <ActionFeedbackToast item={{ id, createdAt: 0, tone, message: t(tone === "success" ? "payments.saved" : errors.temporary.messageKey), durationMs: 3_600_000, actionLabel: t("common.retry"), onAction: recover }} onDismiss={() => setDismissed(true)} />]),
    ["route-error", <RouteErrorView error={new Error("SQLSTATE never-render")} onBack={recover} onHome={recover} />],
    ["payment-uncertain", <StatusNotice tone="warning" title={t("payments.uncertain")} description={t("payments.uncertainClose")} action={action} />],
    ["ai-unavailable", <StatusNotice tone="warning" title={t("aiQuality.unavailable")} action={action} />],
    ["unread-messages", <UnreadMessagesNotice count={5} onOpen={recover} onDismiss={recover} />],
    ["forbidden", <ForbiddenState />],
    ["page-loading", <PageSkeleton />],
    ["app-crash", <AppErrorBoundary><Crash /></AppErrorBoundary>],
    ["undo", <UndoToastProvider><UndoExample /></UndoToastProvider>],
    ["ai-insight", <AiInsightCard icon={AlertTriangle} severity="warning" title={t("aiQuality.unavailable")} description={t("aiQuality.pending")} actionLabel={t("common.retry")} />],
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

createRoot(document.getElementById("root")!).render(<I18nProvider><Catalog /></I18nProvider>);

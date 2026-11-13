import { StrictMode, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { MemoryRouter, useLocation } from "react-router";
import type { Business, CurrentUser } from "../../src/types";
import { InboxNotificationEffects } from "../../src/components/layout/InboxNotificationEffects";
import { NotificationHost } from "../../src/components/notifications/NotificationHost";
import { NotificationProvider, useNotification } from "../../src/components/notifications/NotificationProvider";
import { UndoToastProvider, useUndoToast } from "../../src/components/actions/UndoToastProvider";
import { ConnectivityStatus } from "../../src/components/ui/ConnectivityStatus";
import { Dialog, Drawer } from "../../src/components/ui/Overlay";
import { StatusNotice } from "../../src/components/ui/StatusNotice";
import { FieldErrorSummary } from "../../src/components/ui/FieldErrorSummary";
import { InlineFallback, PermissionFallback } from "../../src/components/ui/FallbackSurfaces";
import { Button } from "../../src/components/ui/Button";
import { useActionFeedback } from "../../src/components/actions/useActionFeedback";
import { appErrorCategories, appErrorCodeRegistry, normalizeAppError } from "../../src/api/appError";
import { I18nProvider, useI18n } from "../../src/lib/i18n";
import "@fontsource-variable/manrope";
import "../../src/styles.css";

const failure = normalizeAppError({ isAxiosError: true, response: { status: 503, data: { code: "temporary_service_failure", request_id: "alert-fixture", retryable: true } } });
const denied = normalizeAppError({ isAxiosError: true, response: { status: 403, data: { code: "permission_denied" } } });
const validation = { ...failure, fieldErrors: { name: ["Example validation"] } };
const business = { id: 77 } as Business;
const user: CurrentUser = { id: 77, email: "alerts@example.test", role: "operator", is_platform_user: false, is_merchant_user: true, is_business_manager: false, businesses: [business], memberships: [{ business: 77, role: "operator", business_role: null, business_role_name: "", is_active: true }], effective_permissions: { "77": [{ resource: "conversations", action: "view", scope: "business" }] } };

function Controls() {
  const { t } = useI18n();
  const notify = useNotification();
  const { notifyError } = useActionFeedback();
  const [errorCategory, setErrorCategory] = useState(failure.category);
  const rawError = errorCategory === "offline" ? { isAxiosError: true } : {
    isAxiosError: true, response: { status: 400, data: { code: appErrorCodeRegistry.find(policy => policy.category === errorCategory)!.code } },
  };
  const currentError = normalizeAppError(rawError);
  const undo = useUndoToast();
  const [dialog, setDialog] = useState(false);
  const [drawer, setDrawer] = useState(false);
  const [nested, setNested] = useState(false);
  const [removeOpener, setRemoveOpener] = useState(false);
  const [counts, setCounts] = useState([0, 0, 0]);
  const pending = useRef<() => void>(() => undefined);
  const reads = useRef(0);
  const location = useLocation();
  const query = useQuery({ queryKey: ["alert-reads"], queryFn: async () => ++reads.current, staleTime: Infinity });
  const count = (index: number) => setCounts(current => current.map((n, i) => n + (i === index ? 1 : 0)));
  const show = () => notify({ title: t("common.saved"), description: t("fallback.recovery.help"), durationMs: 60_000 });
  return <>
    <ConnectivityStatus monitor />
    <InboxNotificationEffects user={user} business={business} activeMembership={user.memberships![0]} />
    <main className="mx-auto max-w-3xl space-y-4 p-4 pb-28">
      <input data-testid="draft" aria-label="Draft" defaultValue="Preserved draft" />
      <output data-testid="counts">{counts.join(",")}</output><output data-testid="reads">{query.data}</output>
      <output data-testid="route">{location.pathname}{location.search}</output>
      <div className="flex flex-wrap gap-3">
        <Button data-testid="show" onClick={show}>{t("common.saved")}</Button>
        <Button data-testid="stack" onClick={() => {
          for (const tone of ["success", "danger", "warning", "info"] as const) notify({ tone, title: t("common.saved"), description: t("fallback.recovery.help"), durationMs: 60_000 });
          undo({ message: t("clients.noticeArchived"), durationMs: 60_000, onUndo: () => count(1) });
        }}>{t("common.open")}</Button>
        <Button data-testid="long" onClick={() => notify({ title: "A".repeat(100), description: t("fallback.recovery.help").repeat(5), durationMs: 60_000 })}>{t("common.open")}</Button>
        <Button data-testid="queue" onClick={() => { for (let n = 0; n < 5; n++) notify({ title: `Queue ${n}`, durationMs: 60_000 }); }}>{t("common.open")}</Button>
        <Button data-testid="queued-short" onClick={() => notify({ title: "Pending short", durationMs: 800 })}>{t("common.open")}</Button>
        <Button data-testid="delayed-queue" onClick={() => window.setTimeout(() => {
          for (let n = 0; n < 5; n++) notify({ title: `Burst ${n}`, durationMs: 60_000 });
        }, 500)}>{t("common.open")}</Button>
        <select data-testid="error-category" aria-label="Fixture error category" value={errorCategory} onChange={event => setErrorCategory(event.target.value as typeof errorCategory)}>
          {appErrorCategories.map(category => <option key={category}>{category}</option>)}
        </select>
        <Button data-testid="error-direct" onClick={() => notify({ appError: currentError })}>{t("common.open")}</Button>
        <Button data-testid="error-feedback" onClick={() => notifyError(rawError)}>{t("common.open")}</Button>
        <Button data-testid="error-override" onClick={() => notifyError(rawError, { tone: "danger" })}>{t("common.open")}</Button>
        <Button data-testid="chat" onClick={() => queryClient.setQueryData(["inbox-summary", 77], { unread_messages: 2 })}>{t("header.openMessages")}</Button>
        {!removeOpener ? <Button data-testid="remove-opener" onClick={() => { show(); setRemoveOpener(true); }}>{t("common.open")}</Button> : null}
        <Button data-testid="short" onClick={() => notify({ message: t("common.saved"), durationMs: 800 })}>{t("common.saved")}</Button>
        <Button data-testid="retry" onClick={() => notify({ message: t("common.retry"), durationMs: 800, actionLabel: t("common.retry"), onAction: () => new Promise<void>(resolve => { count(0); pending.current = resolve; }) })}>{t("common.retry")}</Button>
        <Button data-testid="retry-failure" onClick={() => notify({ appError: failure, durationMs: 60_000, actionLabel: t("common.retry"), onAction: async () => { count(0); throw new Error("fixture retry failed"); } })}>{t("common.retry")}</Button>
        <Button data-testid="release" onClick={() => pending.current()}>{t("common.confirm")}</Button>
        <Button data-testid="undo" onClick={() => undo({ message: t("clients.noticeArchived"), onUndo: async () => { count(1); throw failure; }, onRecover: () => count(2) })}>{t("actions.undo")}</Button>
        <Button data-testid="modal" onClick={() => setDialog(true)}>{t("common.open")}</Button>
        <Button data-testid="drawer" onClick={() => setDrawer(true)}>{t("common.open")}</Button>
      </div>
      <InlineFallback error={failure} onRetry={async () => { count(0); throw failure; }} />
      <div data-testid="error-inline"><InlineFallback error={currentError} /></div>
      <FieldErrorSummary error={validation} fieldLabels={{ name: t("common.name") }} onFieldSelect={() => document.querySelector<HTMLInputElement>('[data-testid="draft"]')?.focus()} />
      <PermissionFallback error={denied} />
      <StatusNotice tone="info" title={t("integrations.card.readOnly")} />
    </main>
    <nav className="fixed inset-x-2 bottom-2 z-[60] h-16 bg-white lg:hidden"><button data-testid="bottom-mobile-menu-trigger">{t("mobile.more")}</button></nav>
    <Dialog title={t("common.open")} open={dialog} onClose={() => setDialog(false)} testId="test-modal">
      <input data-testid="modal-input" aria-label="Modal input" />
      <Button data-testid="modal-toast" onClick={show}>{t("common.saved")}</Button>
      <Button data-testid="nested" onClick={() => setNested(true)}>{t("common.open")}</Button>
      <Dialog title={t("common.open")} open={nested} onClose={() => setNested(false)} testId="nested-modal">
        <Button data-testid="nested-toast" onClick={show}>{t("common.saved")}</Button>
      </Dialog>
    </Dialog>
    <Drawer open={drawer} onClose={() => setDrawer(false)} ariaLabel={t("common.open")} testId="test-drawer">
      <Button data-testid="drawer-toast" onClick={show}>{t("common.saved")}</Button>
      <Button onClick={() => setDrawer(false)}>{t("common.close")}</Button>
    </Drawer>
  </>;
}

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnReconnect: false } } });
createRoot(document.getElementById("root")!).render(<StrictMode><I18nProvider><MemoryRouter><QueryClientProvider client={queryClient}><NotificationHost><NotificationProvider><UndoToastProvider><Controls /></UndoToastProvider></NotificationProvider></NotificationHost></QueryClientProvider></MemoryRouter></I18nProvider></StrictMode>);

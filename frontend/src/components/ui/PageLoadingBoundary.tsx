import { createContext, useContext, useLayoutEffect, useMemo, useState, useSyncExternalStore, type ReactNode } from "react";
import { useI18n } from "../../lib/i18n";
import { LoadingIndicator } from "./LoadingIndicator";
import { createPageLoadingState } from "./pageLoadingState";

const PageLoadingContext = createContext<ReturnType<typeof createPageLoadingState> | null>(null);
const PageVisibleContext = createContext(true);

export function PageLoadingScope({ active, children }: { active: boolean; children: ReactNode }) {
  const state = useContext(PageLoadingContext);
  return <PageLoadingContext.Provider value={active ? state : null}>{children}</PageLoadingContext.Provider>;
}

/** Only visible initial dependencies register here; never pass a global fetching count. */
export function usePageLoading(pending: boolean) {
  const state = useContext(PageLoadingContext);
  const [id] = useState(() => Symbol("page dependency"));
  useLayoutEffect(() => {
    state?.setPending(id, pending);
    return () => state?.setPending(id, false);
  }, [id, pending, state]);
}

export function PageLoadPending({ pending }: { pending: boolean }) {
  usePageLoading(pending);
  return null;
}

export function usePageVisible() {
  return useContext(PageVisibleContext);
}

export function useLocalLoadingScope(scope: "block" | "page") {
  const state = useContext(PageLoadingContext);
  return scope === "page" && state?.isReady() ? "block" : scope;
}

export function PageLoadingBoundary({ children, identity }: { children: ReactNode; identity: unknown }) {
  const state = useMemo(createPageLoadingState, [identity]);
  useSyncExternalStore(state.subscribe, state.snapshot, state.snapshot);
  const ready = state.isReady();
  const parentVisible = usePageVisible();
  const { t } = useI18n();
  usePageLoading(!ready);
  // Descendant layout effects register before this effect, including a Suspense fallback.
  useLayoutEffect(() => { state.revealIfReady(); });
  return <PageLoadingContext.Provider value={state}>
    <PageVisibleContext.Provider value={parentVisible && ready}>
      <div className="platforma-page-content" hidden={!ready} inert={!ready || undefined}>
        {children}
      </div>
      {!ready && <div className="platforma-page-loading" data-testid="page-loading">
        <LoadingIndicator scope="page" label={t("common.loadingData")} />
      </div>}
    </PageVisibleContext.Provider>
  </PageLoadingContext.Provider>;
}

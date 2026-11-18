import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { usePageVisible } from "../../../components/ui/PageLoadingBoundary";
import { useI18n } from "../../../lib/i18n";

export function AgentPreviewPanel({ open, onClose, children }: {
  open: boolean; onClose: () => void; children: ReactNode;
}) {
  const { t } = useI18n();
  const visible = usePageVisible();
  const shown = open && visible;
  const panelRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const [headerBottom, setHeaderBottom] = useState(0);

  useLayoutEffect(() => {
    if (!shown) return;
    const header = document.querySelector<HTMLElement>("[data-app-header]");
    const update = () => setHeaderBottom(header?.getBoundingClientRect().bottom || 0);
    update();
    const observer = new ResizeObserver(update);
    if (header) observer.observe(header);
    window.addEventListener("resize", update);
    return () => { observer.disconnect(); window.removeEventListener("resize", update); };
  }, [shown]);

  useLayoutEffect(() => {
    if (!shown) return;
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const panel = panelRef.current;
    closeRef.current?.focus({ preventScroll: true });
    return () => {
      if (panel?.contains(document.activeElement) && opener?.isConnected) opener.focus({ preventScroll: true });
    };
  }, [shown]);

  useEffect(() => {
    if (!shown) return;
    const closeOnFocusOutside = (event: FocusEvent) => {
      if (event.target instanceof Node && !panelRef.current?.contains(event.target)) onClose();
    };
    document.addEventListener("focusin", closeOnFocusOutside);
    return () => document.removeEventListener("focusin", closeOnFocusOutside);
  }, [shown, onClose]);

  return createPortal(
    <div ref={panelRef} id="agent-preview-panel" role="dialog" aria-modal="false"
      aria-labelledby="agent-preview-title" hidden={!shown} data-testid="agent-preview-panel"
      style={{ top: headerBottom, zIndex: "var(--platforma-z-drawer)" }}
      className={`${shown ? "flex" : "hidden"} fixed bottom-0 right-0 w-full min-w-0 flex-col overflow-hidden border-l border-platforma-border bg-surface shadow-panel sm:w-[max(360px,33.333vw)]`}
      onKeyDown={event => {
        if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); onClose(); }
      }}>
    <div className="flex shrink-0 items-center justify-between gap-3 border-b border-platforma-border px-5 py-3">
      <h3 className="text-base font-semibold" id="agent-preview-title">{t("aiAgents.previewPanelTitle")}</h3>
      <button ref={closeRef} type="button" className="platforma-focus-ring flex min-h-11 min-w-11 items-center justify-center rounded-control text-platforma-subtle hover:bg-surface-hover"
        aria-label={t("common.close")} onClick={onClose}><X size={20} aria-hidden="true" /></button>
    </div>
    <div className="flex min-h-0 flex-1 flex-col p-4 pb-[max(1rem,env(safe-area-inset-bottom))] sm:p-5">{children}</div>
    </div>, document.body,
  );
}

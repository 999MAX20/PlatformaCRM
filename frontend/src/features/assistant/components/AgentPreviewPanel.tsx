import { useEffect, useRef, type ReactNode } from "react";
import { X } from "lucide-react";
import { Drawer } from "../../../components/ui/Overlay";
import { useMediaQuery } from "../../../hooks/useMediaQuery";
import { useI18n } from "../../../lib/i18n";

export function AgentPreviewPanel({ open, onClose, children }: {
  open: boolean; onClose: () => void; children: ReactNode;
}) {
  const { t } = useI18n();
  const inline = useMediaQuery("(min-width: 1280px)");
  const closeRef = useRef<HTMLButtonElement>(null);
  const wasOpen = useRef(false);
  useEffect(() => {
    if (inline && open && !wasOpen.current) closeRef.current?.focus();
    if (inline && !open && wasOpen.current) document.querySelector<HTMLElement>('[data-focus-return-id="agent-preview-trigger"]')?.focus();
    wasOpen.current = open;
  }, [open, inline]);
  const content = <>
    <header className="flex items-center justify-between gap-3 border-b border-platforma-border px-5 py-3">
      <h3 className="text-base font-semibold" id="agent-preview-title">{t("aiAgents.previewPanelTitle")}</h3>
      <button ref={closeRef} type="button" className="platforma-focus-ring flex min-h-11 min-w-11 items-center justify-center rounded-control text-platforma-subtle hover:bg-surface-hover"
        aria-label={t("common.close")} onClick={onClose}><X size={20} aria-hidden="true" /></button>
    </header>
    <div className="min-h-0 overflow-y-auto p-5">{children}</div>
  </>;
  if (!inline) return <Drawer open={open} onClose={onClose} size="detail" titleId="agent-preview-title" testId="agent-preview-panel">{content}</Drawer>;
  return <aside aria-labelledby="agent-preview-title" hidden={!open} data-testid="agent-preview-panel"
    className={`${open ? "flex" : "hidden"} sticky top-[calc(var(--app-header-height)+1.5rem)] max-h-[calc(100dvh-var(--app-header-height)-3rem)] min-w-0 flex-col self-start overflow-hidden rounded-control border border-platforma-border bg-surface`}
    onKeyDown={event => { if (event.key === "Escape") { event.stopPropagation(); onClose(); } }}>
    {content}
  </aside>;
}

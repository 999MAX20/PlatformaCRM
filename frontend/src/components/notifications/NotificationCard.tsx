import { useContext, useEffect, useLayoutEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { useI18n } from "../../lib/i18n";
import { Dialog } from "../ui/Overlay";
import { NotificationLayoutContext } from "./notificationLayout";

export function NotificationCard({ children, leaving = false, order = 0, onReadyChange, onExited }: {
  children: ReactNode;
  leaving?: boolean;
  order?: number;
  onReadyChange?: (ready: boolean) => void;
  onExited?: () => void;
}) {
  const layout = useContext(NotificationLayoutContext);
  const { t } = useI18n();
  const slot = useRef<HTMLDivElement>(null);
  const content = useRef<HTMLDivElement>(null);
  const exitCallback = useRef(onExited);
  exitCallback.current = onExited;
  const [placement, setPlacement] = useState({ visible: !layout, offset: 0, contentHeight: 240 });
  const [entered, setEntered] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [overflow, setOverflow] = useState(false);
  const [pageVisible, setPageVisible] = useState(document.visibilityState === "visible");
  const [hostHidden, setHostHidden] = useState(false);
  useLayoutEffect(() => slot.current && layout ? layout.register(slot.current, setPlacement) : undefined, [layout]);
  useLayoutEffect(() => {
    const node = content.current;
    if (!node) return;
    const measure = () => setOverflow(node.scrollHeight > placement.contentHeight + 1);
    const observer = new ResizeObserver(measure);
    observer.observe(node);
    if (node.firstElementChild) observer.observe(node.firstElementChild);
    measure();
    return () => observer.disconnect();
  }, [children, placement.contentHeight]);
  useEffect(() => {
    setEntered(false);
    if (!placement.visible) return;
    const timer = window.setTimeout(() => setEntered(true), window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 400);
    return () => clearTimeout(timer);
  }, [placement.visible]);
  useEffect(() => {
    const update = () => setPageVisible(document.visibilityState === "visible");
    document.addEventListener("visibilitychange", update);
    return () => document.removeEventListener("visibilitychange", update);
  }, []);
  useEffect(() => {
    const host = slot.current?.closest<HTMLElement>('.platforma-notification-viewport');
    if (!host) return;
    const update = () => setHostHidden(host.inert);
    const observer = new MutationObserver(update);
    observer.observe(host, { attributes: true, attributeFilter: ['inert'] });
    update();
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    onReadyChange?.(placement.visible && entered && !expanded && !leaving && pageVisible && !hostHidden);
    return () => onReadyChange?.(false);
  }, [placement.visible, entered, expanded, leaving, pageVisible, hostHidden, onReadyChange]);
  useEffect(() => { if (leaving) setExpanded(false); }, [leaving]);
  useEffect(() => {
    if (!leaving) return;
    // animationend owns normal removal; the fallback also covers hidden tabs.
    const timer = window.setTimeout(() => exitCallback.current?.(), window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 400);
    return () => clearTimeout(timer);
  }, [leaving]);
  return <>
    <div ref={slot} className={layout ? "platforma-notification-slot" : undefined} data-order={order}
      data-queued={!placement.visible || undefined} data-entering={!entered || undefined} aria-hidden={!placement.visible || expanded || undefined}
      inert={!placement.visible || leaving || expanded}
      style={{ "--notice-offset": `${placement.offset}px`, "--notice-content-height": `${placement.contentHeight}px` } as CSSProperties}>
      <div className="platforma-notification-card" data-leaving={leaving || undefined} data-visible={placement.visible || undefined}
        onAnimationEnd={event => {
          if (event.target !== event.currentTarget) return;
          if (event.animationName === "platforma-notice-exit") exitCallback.current?.();
          if (event.animationName === "platforma-notice-enter") setEntered(true);
        }}>
        <div ref={content} className="platforma-notification-preview">{children}</div>
        {overflow ? <button className="platforma-notification-details" type="button" onClick={() => setExpanded(true)}>{t("notifications.showDetails")}</button> : null}
      </div>
    </div>
    <Dialog open={expanded && !leaving} onClose={() => setExpanded(false)} title={t("notifications.detailsTitle")} testId="notification-details">
      <div className="p-4" data-notification-full-content>{children}</div>
    </Dialog>
  </>;
}

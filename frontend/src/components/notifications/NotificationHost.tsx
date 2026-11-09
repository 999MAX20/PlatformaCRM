import { createContext, useContext, useLayoutEffect, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";

type Group = "connection" | "session" | "undo" | "notifications" | "messages";
const HostContext = createContext<Record<Group, HTMLElement> | null>(null);
const ConnectionNoticeContext = createContext({ unavailable: false, setUnavailable: (_value: boolean) => {} });

export function useConnectionNoticeState() {
  return useContext(ConnectionNoticeContext);
}

export function NotificationHost({ children }: { children: ReactNode }) {
  const [unavailable, setUnavailable] = useState(() => !navigator.onLine);
  const [host] = useState(() => {
    const root = document.createElement("div");
    root.className = "platforma-notification-host";
    root.dataset.testid = "notification-host";
    const groups = {} as Record<Group, HTMLElement>;
    for (const group of ["connection", "session", "undo", "notifications", "messages"] as const) {
      const node = document.createElement("div");
      node.className = "platforma-notification-group";
      node.dataset.notificationGroup = group;
      root.append(node);
      groups[group] = node;
    }
    return { root, groups };
  });

  useLayoutEffect(() => {
    let navigation: HTMLElement | null = null;
    const resize = new ResizeObserver(position);
    function position() {
      const dialogs = Array.from(document.querySelectorAll<HTMLElement>('[role="dialog"][aria-modal="true"]'));
      const parent = dialogs.filter(node => node.getClientRects().length).at(-1) || document.body;
      // Move the stable portal container, preserving mounted actions and timers.
      if (host.root.parentElement !== parent) parent.append(host.root);
      const nav = document.querySelector<HTMLElement>('[data-testid="bottom-mobile-menu-trigger"]')?.closest("nav") || null;
      if (nav !== navigation) {
        if (navigation) resize.unobserve(navigation);
        navigation = nav;
        if (nav) resize.observe(nav);
      }
      const clearance = nav?.getClientRects().length ? Math.max(0, window.innerHeight - nav.getBoundingClientRect().top) : 0;
      host.root.style.setProperty("--notification-nav-clearance", `${clearance}px`);
    }
    position();
    const observer = new MutationObserver(position);
    observer.observe(document.body, { childList: true, subtree: true });
    window.addEventListener("resize", position);
    return () => {
      observer.disconnect();
      resize.disconnect();
      window.removeEventListener("resize", position);
      host.root.remove();
    };
  }, [host]);

  return <HostContext.Provider value={host.groups}><ConnectionNoticeContext.Provider value={{ unavailable, setUnavailable }}>{children}</ConnectionNoticeContext.Provider></HostContext.Provider>;
}

export function NotificationPortal({ group, children }: { group: Group; children: ReactNode }) {
  const host = useContext(HostContext);
  return host ? createPortal(children, host[group]) : <>{children}</>;
}

export function NotificationPresence({ children }: { children: ReactNode }) {
  const [retained, setRetained] = useState(children);
  useLayoutEffect(() => {
    if (children) {
      setRetained(children);
      return;
    }
    const timer = window.setTimeout(() => setRetained(null), window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 200);
    return () => window.clearTimeout(timer);
  }, [children]);
  if (!children && !retained) return null;
  return <div className="platforma-notification-card" data-leaving={!children || undefined} inert={!children}>{children || retained}</div>;
}

export function restoreNoticeFocus(card: HTMLElement | null, opener: HTMLElement | null) {
  if (!card?.contains(document.activeElement)) return;
  const dialog = Array.from(document.querySelectorAll<HTMLElement>('[role="dialog"][aria-modal="true"]'))
    .filter(node => node.getClientRects().length).at(-1);
  const available = (node: HTMLElement | null): node is HTMLElement => Boolean(node?.isConnected
    && node.getClientRects().length && !node.matches('[disabled], [aria-disabled="true"]')
    && !node.closest('[inert], [hidden], [aria-hidden="true"]') && !card.contains(node));
  if (available(opener) && (!dialog || dialog.contains(opener))) {
    opener.focus({ preventScroll: true });
    return;
  }
  const target = Array.from((dialog || document).querySelectorAll<HTMLElement>(
    'button:not([disabled]), a[href], input:not([disabled]), [tabindex="0"]',
  )).find(node => available(node) && !node.closest('[data-testid="notification-host"]'));
  (target || dialog)?.focus({ preventScroll: true });
}

import { useEffect, useLayoutEffect, useRef, useState, type ReactNode, type RefObject } from "react";
import { createPortal } from "react-dom";
import { PopoverSurface } from "./Overlay";
import "./CalendarPopover.css";

export function CalendarPopover({ anchor, label, id, testId, onClose, children }: {
  anchor: RefObject<HTMLElement | null>;
  label: string;
  id?: string;
  testId?: string;
  onClose: (restoreFocus?: boolean) => void;
  children: ReactNode;
}) {
  const panel = useRef<HTMLDivElement>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  const [position, setPosition] = useState({ left: 8, top: 8, maxHeight: 400 });
  // Nested calendars belong to the parent popover's outside-click boundary too.
  const portalRoot = anchor.current?.closest<HTMLElement>('[role="dialog"]') || document.body;
  useLayoutEffect(() => {
    const place = () => {
      const rect = anchor.current?.getBoundingClientRect();
      if (!rect || !panel.current) return;
      const headerBottom = portalRoot === document.body
        ? document.querySelector('[data-app-header]')?.getBoundingClientRect().bottom || 0 : 0;
      const minimumTop = Math.max(8, headerBottom + 8);
      if (rect.bottom <= headerBottom || rect.top >= window.innerHeight) {
        closeRef.current(false);
        return;
      }
      const width = panel.current.offsetWidth;
      const below = window.innerHeight - rect.bottom - 14;
      const above = Math.max(0, rect.top - minimumTop - 6);
      const upward = below < panel.current.scrollHeight && above > below;
      const maxHeight = Math.max(0, upward ? above : window.innerHeight - Math.max(minimumTop, rect.bottom + 6) - 8);
      setPosition({ left: Math.max(8, Math.min(rect.left, window.innerWidth - width - 8)),
        top: upward ? Math.max(minimumTop, rect.top - Math.min(panel.current.scrollHeight, maxHeight) - 6) : Math.max(minimumTop, rect.bottom + 6), maxHeight });
    };
    place();
    (panel.current?.querySelector<HTMLButtonElement>('[data-date][tabindex="0"]:not([disabled])') || panel.current?.querySelector<HTMLButtonElement>('button:not([disabled])'))?.focus({ preventScroll: true });
    const observer = new ResizeObserver(place);
    if (panel.current) observer.observe(panel.current);
    window.addEventListener("resize", place);
    window.addEventListener("scroll", place, true);
    return () => { observer.disconnect(); window.removeEventListener("resize", place); window.removeEventListener("scroll", place, true); };
  }, [anchor, portalRoot]);
  useEffect(() => {
    const outside = (event: PointerEvent | FocusEvent) => {
      if (!panel.current?.contains(event.target as Node) && !anchor.current?.contains(event.target as Node)) onClose(false);
    };
    document.addEventListener("pointerdown", outside);
    document.addEventListener("focusin", outside);
    return () => { document.removeEventListener("pointerdown", outside); document.removeEventListener("focusin", outside); };
  }, [anchor, onClose]);
  function leaveWithTab(event: React.KeyboardEvent<HTMLDivElement>) {
    if (event.key !== "Tab" || event.defaultPrevented || !panel.current) return;
    const selector = 'button:not([disabled]), input:not([disabled]), select:not([disabled]), a[href], [tabindex="0"]';
    const available = (root: ParentNode) => Array.from(root.querySelectorAll<HTMLElement>(selector)).filter(element => element.tabIndex >= 0 && element.getClientRects().length > 0);
    const inside = available(panel.current);
    const edge = event.shiftKey ? inside[0] : inside.at(-1);
    if (document.activeElement !== edge) return;
    event.preventDefault();
    event.stopPropagation();
    const outside = available(portalRoot).filter(element => !panel.current?.contains(element));
    const anchorIndex = outside.indexOf(anchor.current!);
    const next = event.shiftKey ? anchor.current : outside[anchorIndex + 1] || anchor.current;
    onClose(false);
    next?.focus({ preventScroll: true });
  }
  return createPortal(<PopoverSurface ref={panel} id={id} role="dialog" aria-label={label} data-testid={testId}
    className="platforma-calendar-popover fixed z-[var(--platforma-z-popover)] w-[min(384px,calc(100vw-1rem))] overflow-y-auto p-3 sm:p-4" style={position}
    onClick={event => event.stopPropagation()}
    onKeyDown={event => { if (event.key === "Escape" && !event.defaultPrevented) { event.preventDefault(); event.stopPropagation(); onClose(); } else leaveWithTab(event); }}>
    {children}
  </PopoverSurface>, portalRoot);
}

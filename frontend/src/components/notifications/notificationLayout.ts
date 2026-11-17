import { createContext } from "react";

export type NoticePlacement = { visible: boolean; offset: number; contentHeight: number };
type Entry = { node: HTMLElement; update: (value: NoticePlacement) => void; placement: NoticePlacement };
export const NotificationLayoutContext = createContext<ReturnType<typeof createNotificationLayout> | null>(null);

export function createNotificationLayout(stack: HTMLElement) {
  const entries = new Map<HTMLElement, Entry>();
  let observer: ResizeObserver | undefined;
  let frame = 0;
  function layout() {
    // Reserve every slot until an exit finishes, including simultaneous exits.
    if (Array.from(entries.values()).some(entry => entry.placement.visible && entry.node.querySelector("[data-leaving]"))) return;
    const available = stack.clientHeight;
    const mobile = window.matchMedia("(max-width: 760px)").matches;
    const contentHeight = Math.max(48, Math.min(240, available - 52));
    const groups = ["connection", "session", "undo", "notifications", "messages"];
    const group = (entry: Entry) => entry.node.closest<HTMLElement>("[data-notification-group]")?.dataset.notificationGroup || "notifications";
    const visualOrder = (a: Entry, b: Entry) => groups.indexOf(group(a)) - groups.indexOf(group(b)) || Number(a.node.dataset.order || 0) - Number(b.node.dataset.order || 0);
    const ordered = Array.from(entries.values()).sort((a, b) => {
      const engaged = (entry: Entry) => entry.placement.visible && (entry.node.matches(":hover, :focus-within") || Boolean(entry.node.querySelector("button:disabled")));
      if (engaged(a) !== engaged(b)) return engaged(a) ? -1 : 1;
      // System state takes precedence; an engaged action keeps its place.
      return visualOrder(a, b);
    });
    let used = 0;
    let ordinary = 0;
    const admitted = new Set<Entry>();
    for (const entry of ordered) {
      const isOrdinary = entry.node.closest<HTMLElement>("[data-notification-group]")?.dataset.notificationGroup === "notifications";
      const height = entry.node.offsetHeight;
      const visible = height > 0 && used + height <= available + 1 && (!isOrdinary || ordinary < (mobile ? 1 : 4));
      if (visible) { admitted.add(entry); used += height + 8; if (isOrdinary) ordinary++; }
    }
    used = 0;
    for (const entry of ordered.sort(visualOrder)) {
      const visible = admitted.has(entry);
      const exiting = entry.placement.visible && entry.node.querySelector("[data-leaving]");
      const offset = exiting ? entry.placement.offset : used;
      const next = { visible, offset, contentHeight };
      if (visible) used = Math.max(used, offset + entry.node.offsetHeight + 8);
      if (Object.keys(next).some(key => next[key as keyof NoticePlacement] !== entry.placement[key as keyof NoticePlacement])) {
        entry.placement = next;
        entry.update(next);
      }
    }
  }
  function schedule() {
    cancelAnimationFrame(frame);
    frame = requestAnimationFrame(layout);
  }
  return {
    start() {
      observer = new ResizeObserver(schedule);
      observer.observe(stack);
      for (const node of entries.keys()) observer.observe(node);
      for (const event of ["pointerover", "pointerout", "focusin", "focusout"]) stack.addEventListener(event, schedule);
      schedule();
      return () => {
        observer?.disconnect(); observer = undefined; cancelAnimationFrame(frame);
        for (const event of ["pointerover", "pointerout", "focusin", "focusout"]) stack.removeEventListener(event, schedule);
      };
    },
    register(node: HTMLElement, update: Entry["update"]) {
      entries.set(node, { node, update, placement: { visible: false, offset: 0, contentHeight: 240 } });
      observer?.observe(node);
      layout();
      return () => { observer?.unobserve(node); entries.delete(node); schedule(); };
    },
  };
}

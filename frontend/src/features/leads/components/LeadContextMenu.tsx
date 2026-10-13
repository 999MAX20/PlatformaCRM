import {
  Archive,
  CircleDot,
  MessageCircle,
  Phone,
  UserCheck,
} from "lucide-react";
import { createPortal } from "react-dom";
import { useLayoutEffect, useRef, useState } from "react";

import { PopoverSurface } from "../../../components/ui/Overlay";
import { cn } from "../../../lib/cn";
import type { Lead } from "../../../types";

export function LeadContextMenu({
  x,
  y,
  lead,
  labels,
  onClose,
  onOpen,
  onCall,
  onWhatsApp,
  onTake,
  onArchive,
}: {
  x: number;
  y: number;
  lead: Lead;
  labels: {
    open: string;
    call: string;
    whatsApp: string;
    assignToMe: string;
    archive: string;
  };
  onClose: () => void;
  onOpen: (lead: Lead) => void;
  onCall: (lead: Lead) => void;
  onWhatsApp: (lead: Lead) => void;
  onTake: (lead: Lead) => void;
  onArchive: (lead: Lead) => void;
}) {
  const menu = useRef<HTMLDivElement>(null);
  const returnFocus = useRef(document.activeElement instanceof HTMLElement ? document.activeElement : null);
  const [position, setPosition] = useState({ left: 8, top: 8 });
  useLayoutEffect(() => {
    const place = () => {
      const bounds = menu.current?.getBoundingClientRect();
      if (!bounds) return;
      setPosition({
        left: Math.max(8, Math.min(x, window.innerWidth - bounds.width - 8)),
        top: Math.max(8, Math.min(y, window.innerHeight - bounds.height - 8)),
      });
    };
    place();
    menu.current?.querySelector<HTMLButtonElement>('[role="menuitem"]')?.focus();
    window.addEventListener("resize", place);
    return () => window.removeEventListener("resize", place);
  }, [x, y]);
  function close() {
    onClose();
    returnFocus.current?.focus({ preventScroll: true });
  }
  const items: Array<{
    label: string;
    icon: typeof CircleDot;
    onClick: () => void;
    tone?: "warning";
  }> = [
    { label: labels.open, icon: CircleDot, onClick: () => onOpen(lead) },
    { label: labels.call, icon: Phone, onClick: () => onCall(lead) },
    {
      label: labels.whatsApp,
      icon: MessageCircle,
      onClick: () => onWhatsApp(lead),
    },
    { label: labels.assignToMe, icon: UserCheck, onClick: () => onTake(lead) },
    { label: labels.archive, icon: Archive, onClick: () => onArchive(lead), tone: "warning" },
  ];

  return createPortal(
    <div className="fixed inset-0 z-[var(--platforma-z-popover)]" onClick={close} onContextMenu={event => { event.preventDefault(); close(); }}>
      <PopoverSurface
        ref={menu}
        role="menu"
        aria-label={labels.open}
        data-testid="lead-context-menu"
        className="fixed max-h-[calc(100dvh-16px)] w-56 max-w-[calc(100vw-16px)] overflow-y-auto p-1.5"
        style={position}
        onClick={(event) => event.stopPropagation()}
        onKeyDown={event => {
          const buttons = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>('[role="menuitem"]'));
          const index = buttons.indexOf(document.activeElement as HTMLButtonElement);
          if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); close(); }
          if (event.key === "Tab") close();
          if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
            event.preventDefault();
            const next = event.key === "Home" ? 0 : event.key === "End" ? buttons.length - 1 : (index + (event.key === "ArrowDown" ? 1 : -1) + buttons.length) % buttons.length;
            buttons[next]?.focus();
          }
        }}
      >
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.label}
              type="button"
              role="menuitem"
              className={cn(
                "platforma-focus-ring flex min-h-10 w-full items-center gap-2 rounded-control px-3 py-2 text-left text-sm font-semibold hover:bg-surface-hover",
                item.tone === "warning" ? "text-platforma-warning hover:bg-[var(--platforma-warning-soft)]" : "text-platforma-text",
              )}
              onClick={() => {
                close();
                item.onClick();
              }}
            >
              <Icon size={16} />
              {item.label}
            </button>
          );
        })}
      </PopoverSurface>
    </div>, document.body,
  );
}

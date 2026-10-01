import { useEffect, useId, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { Button } from "../ui/Button";
import { PopoverSurface } from "../ui/Overlay";

/** A bounded form popover that remains outside the workspace scroll container. */
export function CrmWorkspacePopover({ label, icon, children, open: controlledOpen, onToggle, count = 0 }: {
  label: string;
  icon?: ReactNode;
  children: ReactNode;
  open?: boolean;
  onToggle?: () => void;
  count?: number;
}) {
  const [localOpen, setLocalOpen] = useState(false);
  const open = controlledOpen ?? localOpen;
  const toggle = onToggle ?? (() => setLocalOpen((value) => !value));
  const trigger = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const id = useId();
  const [position, setPosition] = useState({ left: 8, top: 8, maxHeight: 400 });

  useLayoutEffect(() => {
    if (!open) return;
    const place = () => {
      const rect = trigger.current?.getBoundingClientRect();
      if (!rect) return;
      const width = panel.current?.offsetWidth ?? 360;
      const top = Math.min(rect.bottom + 6, Math.max(8, window.innerHeight - 160));
      setPosition({ left: Math.max(8, Math.min(rect.right - width, window.innerWidth - width - 8)), top, maxHeight: window.innerHeight - top - 8 });
    };
    place();
    panel.current?.focus({ preventScroll: true });
    window.addEventListener("resize", place);
    window.addEventListener("scroll", place, true);
    return () => {
      window.removeEventListener("resize", place);
      window.removeEventListener("scroll", place, true);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const outside = (event: PointerEvent) => {
      if (!panel.current?.contains(event.target as Node) && !trigger.current?.contains(event.target as Node)) toggle();
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      if (event.target instanceof Element && event.target.closest('[role="combobox"][aria-expanded="true"]')) return;
      event.preventDefault();
      event.stopPropagation();
      toggle();
      trigger.current?.focus({ preventScroll: true });
    };
    document.addEventListener("pointerdown", outside);
    document.addEventListener("keydown", escape, true);
    return () => {
      document.removeEventListener("pointerdown", outside);
      document.removeEventListener("keydown", escape, true);
    };
  }, [open, toggle]);

  return <>
    <Button ref={trigger} variant="secondary" size="sm" className="h-10 shrink-0 gap-2 px-3" aria-expanded={open} aria-controls={open ? id : undefined} aria-haspopup="dialog" onClick={toggle}>
      {icon}{label}{count > 0 ? <span className="rounded bg-surface-muted px-1.5 tabular-nums">{count}</span> : null}
    </Button>
    {open ? createPortal(<PopoverSurface ref={panel} id={id} role="dialog" aria-label={label} tabIndex={-1}
      className="fixed z-[80] w-[min(420px,calc(100vw-1rem))] overflow-y-auto p-4 outline-none" style={position}>
      {children}
    </PopoverSurface>, document.body) : null}
  </>;
}

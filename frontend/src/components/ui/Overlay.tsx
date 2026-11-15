import { X } from "lucide-react";
import { createPortal } from "react-dom";
import {
  HTMLAttributes,
  forwardRef,
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  type ReactNode,
} from "react";

import { useBodyScrollLock } from "../../hooks/useBodyScrollLock";
import { cn } from "../../lib/cn";
import { useI18n } from "../../lib/i18n";
import { usePageVisible } from "./PageLoadingBoundary";

type OverlaySize = "sm" | "md" | "lg" | "xl";
type DrawerSize = "detail" | "complex" | "custom";

const dialogSizeClass: Record<OverlaySize, string> = {
  sm: "max-w-lg",
  md: "max-w-2xl",
  lg: "max-w-4xl",
  xl: "max-w-6xl",
};

const drawerSizeClass: Record<DrawerSize, string> = {
  detail: "max-w-[520px]",
  complex: "max-w-[720px]",
  custom: "",
};

function CloseButton({ onClose }: { onClose: () => void }) {
  const { t } = useI18n();
  return (
    <button
      type="button"
      className="platforma-focus-ring platforma-touch-target inline-flex shrink-0 items-center justify-center rounded-control text-platforma-faint transition hover:bg-surface-hover hover:text-platforma-text"
      onClick={onClose}
      aria-label={t("common.close")}
    >
      <X size={20} strokeWidth={2.2} />
    </button>
  );
}

const focusableSelector = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

function isTopmostDialog(dialog: HTMLElement) {
  const dialogs = Array.from(
    document.querySelectorAll<HTMLElement>('[role="dialog"][aria-modal="true"]'),
  );
  return dialogs.at(-1) === dialog;
}

function canReceiveFocus(element: HTMLElement | null) {
  if (!element?.isConnected) return false;
  if (
    element.matches(
      "[disabled], [aria-disabled='true'], [aria-hidden='true'], [hidden]",
    )
  ) {
    return false;
  }
  return element.getClientRects().length > 0;
}

function focusAndConfirm(element: HTMLElement | null) {
  if (!element || !canReceiveFocus(element)) return false;
  element.focus({ preventScroll: true });
  return document.activeElement === element;
}

function findVisibleFocusReturnTarget(focusReturnId: string | null) {
  if (!focusReturnId) return null;
  return Array.from(
    document.querySelectorAll<HTMLElement>(
      `[data-focus-return-id="${CSS.escape(focusReturnId)}"]`,
    ),
  ).find(canReceiveFocus) || null;
}

function restoreDialogFocus(
  opener: HTMLElement | null,
  focusReturnId: string | null,
) {
  function tryRestore() {
    if (focusAndConfirm(findVisibleFocusReturnTarget(focusReturnId))) return true;
    return focusAndConfirm(opener);
  }

  if (tryRestore()) return;

  let observer: MutationObserver | null = null;
  let timeoutId: number | null = null;
  window.requestAnimationFrame(() => {
    if (tryRestore()) return;
    observer = new MutationObserver(() => {
      if (!tryRestore()) return;
      observer?.disconnect();
      observer = null;
      if (timeoutId !== null) window.clearTimeout(timeoutId);
    });
    observer.observe(document.body, {
      attributes: true,
      attributeFilter: ["class", "hidden", "style"],
      childList: true,
      subtree: true,
    });
    timeoutId = window.setTimeout(() => {
      observer?.disconnect();
      observer = null;
    }, 1_000);
  });
}

function useDialogFocus(
  open: boolean,
  onClose: () => void,
  dialogRef: React.RefObject<HTMLElement | null>,
  preferredFocusReturnId?: string,
) {
  useLayoutEffect(() => {
    if (!open) return undefined;

    const opener =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    const focusReturnId = preferredFocusReturnId || opener?.dataset.focusReturnId || null;
    const focusInsideDialog = () => {
      const dialog = dialogRef.current;
      if (!dialog || !isTopmostDialog(dialog)) return;
      const autofocusTarget =
        dialog.querySelector<HTMLElement>("[autofocus]");
      const firstFocusable =
        dialog.querySelector<HTMLElement>(focusableSelector);
      focusAndConfirm(autofocusTarget || firstFocusable || dialog);
    };

    focusInsideDialog();
    const frameId = window.requestAnimationFrame(() => {
      const dialog = dialogRef.current;
      if (dialog?.contains(document.activeElement)) return;
      focusInsideDialog();
    });

    return () => {
      window.cancelAnimationFrame(frameId);
      restoreDialogFocus(opener, focusReturnId);
    };
  }, [dialogRef, open, preferredFocusReturnId]);

  useEffect(() => {
    if (!open) return undefined;

    function handleKeyDown(event: KeyboardEvent) {
      if (event.defaultPrevented) return;
      const dialog = dialogRef.current;
      if (!dialog || !isTopmostDialog(dialog)) return;
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        onClose();
        return;
      }
      if (event.key !== "Tab") return;

      const focusable = Array.from(
        dialog.querySelectorAll<HTMLElement>(focusableSelector),
      ).filter(
        (element) =>
          !element.hasAttribute("disabled") &&
          element.getAttribute("aria-hidden") !== "true" &&
          element.getClientRects().length > 0,
      );
      if (!focusable.length) {
        event.preventDefault();
        dialog.focus({ preventScroll: true });
        return;
      }

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const activeElement = document.activeElement;
      if (event.shiftKey && (activeElement === first || !dialog.contains(activeElement))) {
        event.preventDefault();
        last.focus({ preventScroll: true });
      } else if (
        !event.shiftKey &&
        (activeElement === last || !dialog.contains(activeElement))
      ) {
        event.preventDefault();
        first.focus({ preventScroll: true });
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [dialogRef, onClose, open]);
}

export function Dialog({
  title,
  open,
  onClose,
  children,
  size = "md",
  className,
  bodyClassName,
  closeOnBackdrop = true,
  testId,
  focusReturnId,
  presentation = "dialog",
  headerActions,
  footer,
}: {
  title: string;
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
  size?: OverlaySize;
  className?: string;
  bodyClassName?: string;
  closeOnBackdrop?: boolean;
  testId?: string;
  focusReturnId?: string;
  presentation?: "dialog" | "entity";
  headerActions?: ReactNode;
  footer?: ReactNode;
}) {
  const titleId = useId();
  const dialogRef = useRef<HTMLElement>(null);
  const visible = usePageVisible();
  const shown = open && visible;
  useBodyScrollLock(shown);
  useDialogFocus(shown, onClose, dialogRef, focusReturnId);

  if (!shown) return null;

  return createPortal(
    <div
      className="platforma-overlay-backdrop fixed inset-0 grid place-items-center p-3 sm:p-5"
      style={{ zIndex: presentation === "entity" ? "var(--platforma-z-drawer)" : "var(--platforma-z-modal)", ...(presentation === "entity" ? { backdropFilter: "none" } : {}) }}
      onMouseDown={closeOnBackdrop ? onClose : undefined}
    >
      <section
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        data-testid={testId}
        tabIndex={-1}
        autoFocus
        className={cn(
          "platforma-dialog-surface flex w-full flex-col overflow-hidden",
          presentation === "entity"
            ? "h-[calc(100dvh-1.5rem)] max-h-[calc(100dvh-1.5rem)] max-w-[1080px] sm:h-[90dvh] sm:max-h-[90dvh]"
            : cn("max-h-[calc(100dvh-1.5rem)] sm:max-h-[90vh]", dialogSizeClass[size]),
          className,
        )}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header role="presentation" className="flex h-16 shrink-0 items-center justify-between gap-3 border-b border-platforma-border bg-surface-card px-4 sm:px-5">
          <h2 id={titleId} className="min-w-0 truncate text-lg font-semibold text-platforma-ink">
            {title}
          </h2>
          <div className="flex shrink-0 items-center gap-3">{headerActions}<CloseButton onClose={onClose} /></div>
        </header>
        <div className={cn("min-h-0 flex-1", presentation === "entity" ? "flex flex-col overflow-y-auto bg-surface-card md:overflow-hidden" : "overflow-auto bg-surface-warm p-4 sm:p-5", bodyClassName)}>{children}</div>
        {footer ? <footer className="shrink-0 border-t border-platforma-border bg-surface-card px-4 py-3 sm:px-6">{footer}</footer> : null}
      </section>
    </div>,
    document.body,
  );
}

export function Drawer({
  open,
  onClose,
  children,
  id,
  titleId,
  ariaLabel,
  className,
  backdropClassName,
  closeOnBackdrop = true,
  side = "right",
  size = "complex",
  testId,
}: {
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
  id?: string;
  titleId?: string;
  ariaLabel?: string;
  className?: string;
  backdropClassName?: string;
  closeOnBackdrop?: boolean;
  side?: "left" | "right";
  size?: DrawerSize;
  testId?: string;
}) {
  const drawerRef = useRef<HTMLElement>(null);
  const visible = usePageVisible();
  const shown = open && visible;
  useBodyScrollLock(shown);
  useDialogFocus(shown, onClose, drawerRef);

  if (!shown) return null;

  return createPortal(
    <div
      className={cn("platforma-overlay-backdrop fixed inset-0", backdropClassName)}
      style={{ zIndex: "var(--platforma-z-drawer)" }}
      onMouseDown={closeOnBackdrop ? onClose : undefined}
    >
      <aside
        id={id}
        ref={drawerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-label={titleId ? undefined : ariaLabel}
        tabIndex={-1}
        autoFocus
        data-testid={testId}
        className={cn(
          "platforma-drawer-surface flex h-full w-full flex-col overflow-clip",
          drawerSizeClass[size],
          side === "left"
            ? "mr-auto sm:rounded-r-[16px]"
            : "ml-auto sm:rounded-l-[16px]",
          className,
        )}
        onMouseDown={(event) => event.stopPropagation()}
      >
        {children}
      </aside>
    </div>,
    document.body,
  );
}

export const PopoverSurface = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement> & { children: React.ReactNode }>(function PopoverSurface(
  { children, className, ...props },
  ref,
) {
  return (
    <div ref={ref} className={cn("platforma-popover-surface", className)} {...props}>
      {children}
    </div>
  );
});

export function ToastSurface({
  children,
  className,
  onMouseEnter,
  onMouseLeave,
}: {
  children: React.ReactNode;
  className?: string;
  onMouseEnter?: () => void;
  onMouseLeave?: () => void;
}) {
  return createPortal(
    <div
      className={cn("platforma-toast-surface fixed bottom-5 right-5 flex max-w-sm items-center gap-3 px-4 py-3", className)}
      style={{ zIndex: "var(--platforma-z-toast)" }}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      {children}
    </div>,
    document.body,
  );
}

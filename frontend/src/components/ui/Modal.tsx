import { Dialog } from "./Overlay";

export function Modal({
  title,
  open,
  onClose,
  children,
  size,
  className,
  bodyClassName,
  closeOnBackdrop,
  testId,
  focusReturnId,
  footer,
}: {
  title: React.ReactNode;
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
  size?: "sm" | "md" | "lg" | "xl";
  className?: string;
  bodyClassName?: string;
  closeOnBackdrop?: boolean;
  testId?: string;
  focusReturnId?: string;
  footer?: React.ReactNode;
}) {
  return (
    <Dialog
      title={title}
      open={open}
      onClose={onClose}
      size={size}
      className={className}
      bodyClassName={bodyClassName}
      closeOnBackdrop={closeOnBackdrop}
      testId={testId}
      focusReturnId={focusReturnId}
      footer={footer}
    >
      {children}
    </Dialog>
  );
}

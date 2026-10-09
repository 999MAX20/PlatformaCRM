import { Check, ChevronDown, X } from "lucide-react";
import { useId, type ReactNode } from "react";
import { Card } from "../../../components/ui/Card";
import { Drawer } from "../../../components/ui/Overlay";
import { ErrorState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";

export function SettingsSection({ id, active, title, actions, children }: { id: string; active: string; title: string; actions?: ReactNode; children: ReactNode; }) {
  return <Card id={id} hidden={active !== id} className="min-w-0 scroll-mt-20 shadow-none">
    <header className="flex flex-wrap items-center justify-between gap-3 border-b border-platforma-border p-4 sm:px-5 sm:py-5">
      <h1 className="text-[22px] font-bold leading-[30px] text-platforma-text">{title}</h1>
      {actions}
    </header>
    {children}
  </Card>;
}

export function SettingsTabs<T extends string>({ value, onChange, items, label }: { value: T; onChange: (value: T) => void; items: { value: T; label: string; }[]; label: string; }) {
  return <div role="group" aria-label={label} className="flex flex-wrap gap-x-4 gap-y-1 border-b border-platforma-border">
    {items.map(item => <button key={item.value} type="button" aria-pressed={value === item.value}
      onClick={() => onChange(item.value)}
      className={"platforma-focus-ring min-h-11 border-b-2 px-1 py-3 text-sm font-semibold " + (value === item.value ? "border-brand-500 text-brand-700" : "border-transparent text-platforma-subtle hover:text-platforma-text")}>
      {item.label}
    </button>)}
  </div>;
}

export function SettingsFeedback({ error, saved }: { error?: unknown; saved?: boolean; }) {
  const { t } = useI18n();
  if (error) return <ErrorState error={error} />;
  return saved ? <p role="status" className="flex items-center gap-2 text-sm text-platforma-success"><Check aria-hidden="true" size={16} />{t("common.saved")}</p> : null;
}

export function SettingsSaveBar({ children, feedback, drawer = false }: { children: ReactNode; feedback?: ReactNode; drawer?: boolean; }) {
  return <div className={"sticky z-10 mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-platforma-border bg-surface-card px-4 py-3 sm:px-5 " + (drawer ? "bottom-0" : "bottom-[calc(5rem+env(safe-area-inset-bottom))] lg:bottom-0")}>
    <div className="min-w-0 flex-1 basis-48">{feedback}</div>
    <div className="flex flex-wrap items-center gap-2">{children}</div>
  </div>;
}

export function SettingsReference({ children }: { children: ReactNode; }) {
  const { t } = useI18n();
  return <details className="group border-t border-platforma-border pt-3">
    <summary className="platforma-focus-ring flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 rounded-control text-sm font-semibold text-platforma-text">
      {t("settings.redesign.reference")}<ChevronDown aria-hidden="true" size={16} className="group-open:rotate-180" />
    </summary>
    <div className="space-y-4 py-3">{children}</div>
  </details>;
}

export function SettingsDrawer({ open, onClose, title, children, footer }: { open: boolean; onClose: () => void; title: string; children: ReactNode; footer?: ReactNode; }) {
  const titleId = useId();
  const { t } = useI18n();
  return <Drawer open={open} onClose={onClose} titleId={titleId} size="detail" className="bg-surface-card">
    <header className="flex shrink-0 items-center justify-between gap-3 border-b border-platforma-border p-4 sm:p-5">
      <h2 id={titleId} className="text-lg font-bold text-platforma-text">{title}</h2>
      <button type="button" onClick={onClose} aria-label={t("common.close")} className="platforma-focus-ring grid h-11 w-11 shrink-0 place-items-center rounded-control text-platforma-subtle hover:bg-surface-hover"><X size={20} /></button>
    </header>
    <div className="min-h-0 flex-1 overflow-y-auto p-4 sm:p-5">{children}</div>
    {footer}
  </Drawer>;
}

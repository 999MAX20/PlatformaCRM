type LoadingIndicatorProps = {
  label: string;
  scope?: "block" | "page";
};

// No i18n hook here: the same indicator also renders while dictionaries load.
export function LoadingIndicator({ label, scope = "block" }: LoadingIndicatorProps) {
  return (
    <div className={`platforma-loading platforma-loading--${scope}`} role="status" aria-live="polite" aria-busy="true" aria-label={label}>
      <div className="platforma-loading__content">
        <span className="platforma-loading__ring" aria-hidden="true" />
        <span className="text-sm font-medium leading-6 text-platforma-subtle">{label}</span>
      </div>
    </div>
  );
}

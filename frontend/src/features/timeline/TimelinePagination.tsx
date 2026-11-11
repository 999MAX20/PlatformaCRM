import { ChevronLeft, ChevronRight } from "lucide-react";
import { useI18n } from "../../lib/i18n";

export function TimelinePagination({ total, page, pageSize, disabled, onPageChange, onPageSizeChange }: {
  total: number;
  page: number;
  pageSize: number;
  disabled: boolean;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
}) {
  const { t } = useI18n();
  const pages = Math.max(1, Math.ceil(total / pageSize));
  const from = total ? (page - 1) * pageSize + 1 : 0;
  const to = Math.min(page * pageSize, total);
  const arrowClass = "platforma-focus-ring grid h-11 w-11 shrink-0 place-items-center rounded-control text-platforma-text hover:bg-surface-hover disabled:cursor-not-allowed disabled:text-disabled-content sm:h-9 sm:w-9";

  return (
    <fieldset disabled={disabled} className="min-w-0" aria-label={t("pagination.navigation")}>
      <div data-testid="timeline-flat-pagination" className="flex items-center gap-1 whitespace-nowrap text-sm tabular-nums sm:gap-3">
        <select
          aria-label={t("timeline.pageSize")}
          value={pageSize}
          onChange={event => onPageSizeChange(Number(event.target.value))}
          className="platforma-focus-ring min-h-11 w-[76px] shrink-0 rounded-control border-0 bg-transparent px-1 text-sm text-platforma-text hover:bg-surface-hover disabled:cursor-not-allowed disabled:text-disabled-content sm:min-h-9"
        >
          {[10, 20, 30, 50, 100].map(size => <option key={size} value={size}>{t("timeline.perPage", { count: size })}</option>)}
        </select>
        <span aria-hidden="true" className="hidden h-5 w-px bg-platforma-border sm:block" />
        <span aria-live="polite" className="min-w-0 whitespace-normal text-platforma-subtle sm:whitespace-nowrap">{t("timeline.compactRange", { from: `${from}\u2060`, to: `\u2060${to}`, total })}</span>
        <div className="flex shrink-0 items-center">
          <button type="button" className={arrowClass} aria-label={t("pagination.previous")} disabled={page <= 1} onClick={() => onPageChange(page - 1)}><ChevronLeft size={18} aria-hidden="true" /></button>
          <button type="button" className={arrowClass} aria-label={t("pagination.next")} disabled={page >= pages} onClick={() => onPageChange(page + 1)}><ChevronRight size={18} aria-hidden="true" /></button>
        </div>
      </div>
    </fieldset>
  );
}

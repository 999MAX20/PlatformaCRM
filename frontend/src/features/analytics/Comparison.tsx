import { useI18n } from "../../lib/i18n";
import type { AnalyticsWorkspace, WorkspaceRecordFilter, WorkspaceRecordSelection } from "../../types/analyticsWorkspace";
import { comparisonChange } from "./comparisonValues";

export type RecordOpener = (selection: WorkspaceRecordSelection) => void;
export type ReportProps = { data: AnalyticsWorkspace; onRecords: RecordOpener };

export function RecordMetric({ data, label, value, previous, filters, percent = false, onRecords }: ReportProps & {
  label: string; value: number | null; previous: number | null; filters: WorkspaceRecordFilter; percent?: boolean;
}) {
  const { t, language } = useI18n();
  const number = (n: number | null) => n === null ? "—" : `${new Intl.NumberFormat(language).format(n)}${percent ? "%" : ""}`;
  const change = comparisonChange(value, previous);
  const comparison = data.comparison;
  const linkClass = "platforma-focus-ring min-h-11 sm:min-h-6 rounded-control underline decoration-platforma-border underline-offset-4 hover:text-brand-600";
  return <span className="block">
    {value === null ? "—" : <button type="button" className={linkClass} aria-label={t("analyticsWorkspace.openRecords", { name: label, value: number(value) })} onClick={() => onRecords({ title: label, period: data.period, filters })}>{number(value)}</button>}
    {comparison?.available ? <span className="block text-xs font-normal leading-5 text-platforma-subtle">
      <span>{t("analyticsWorkspace.previous")}: </span>
      {previous === null ? "—" : <button type="button" className={linkClass} aria-label={t("analyticsWorkspace.openPreviousRecords", { name: label, value: number(previous) })} onClick={() => onRecords({ title: label, period: comparison.period, filters })}>{number(previous)}</button>}
      {change ? <span className="block">{new Intl.NumberFormat(language, { signDisplay: "exceptZero", maximumFractionDigits: 1 }).format(change.absolute)}{percent ? ` ${t("analyticsWorkspace.pp")}` : change.percent === null ? "" : ` (${new Intl.NumberFormat(language, { signDisplay: "exceptZero", maximumFractionDigits: 1 }).format(change.percent)}%)`}</span> : null}
    </span> : null}
  </span>;
}

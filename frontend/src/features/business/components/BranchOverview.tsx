import type { BranchConfiguration } from "../../../api/branches";
import { Button } from "../../../components/ui/Button";
import { useI18n } from "../../../lib/i18n";

export function BranchOverview({ config, onOpen }: { config: BranchConfiguration; onOpen: (section: string) => void }) {
  const { t } = useI18n();
  const days = config.days.filter(day => day.resource === null && day.date === null);
  const hasHours = days.some(day => day.intervals.length > 0);
  const rows = [
    { key: "services", label: t("branches.services"), value: t("branches.selectedCount", { count: config.offers.filter(row => row.is_active).length }) },
    { key: "specialists", label: t("branches.specialists"), value: t("branches.selectedCount", { count: config.assignments.filter(row => row.is_active).length }) },
    { key: "resources", label: t("branches.physicalResources"), value: t("branches.selectedCount", { count: config.physical_resources.filter(row => row.is_active).length }) },
    { key: "schedule", label: t("nav.workingHours"), value: t(hasHours ? "branches.scheduleConfigured" : "branches.scheduleMissing") },
  ];
  return <div className="space-y-6">
    <dl className="divide-y divide-platforma-border rounded-card border border-platforma-border">
      {rows.map(row => <div key={row.key} className="grid gap-2 p-4 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] sm:items-center">
        <dt className="text-sm font-semibold">{row.label}</dt>
        <dd className="text-sm text-platforma-subtle">{row.value}</dd>
        <dd><Button variant="secondary" onClick={() => onOpen(row.key)}>{t(row.key === "schedule" ? "branches.openSchedule" : "branches.configure")}</Button></dd>
      </div>)}
    </dl>
    <section aria-label={t("nav.workingHours")} className="space-y-3">
      <h3 className="text-base font-semibold">{t("nav.workingHours")}</h3>
      <dl className="divide-y divide-platforma-border rounded-card border border-platforma-border">
        {Array.from({ length: 7 }, (_, weekday) => {
          const day = days.find(item => item.weekday === weekday);
          return <div key={weekday} className="grid grid-cols-[minmax(0,1fr)_minmax(0,2fr)] gap-3 px-4 py-3 text-sm">
            <dt className="font-medium">{t(["weekday.mon", "weekday.tue", "weekday.wed", "weekday.thu", "weekday.fri", "weekday.sat", "weekday.sun"][weekday])}</dt>
            <dd className="tabular-nums">{day ? day.intervals.length ? day.intervals.map(interval => `${interval.start}–${interval.end}`).join(", ") : t("workingHours.dayOff") : "—"}</dd>
          </div>;
        })}
      </dl>
    </section>
  </div>;
}

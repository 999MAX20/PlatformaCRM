import { SettingsSection } from "../components/SettingsLayout";
import { SettingsQueryState } from "../components/SettingsQueryState";
import { formatMetric } from "../settingsUtils";
import type { SettingsModel } from "../useSettingsModel";

export function UsageSection({ model }: { model: SettingsModel; }) {
  const { t, activeSettingsSection, entitlements, locale } = model;
  return <SettingsSection id="usage" active={activeSettingsSection} title={t("settings.section.usage")}>
    <div className="p-4 sm:p-5">
      <SettingsQueryState queries={[entitlements]} />
      {entitlements.isSuccess && <>
        <div className="hidden grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,0.8fr)] gap-4 border-b border-platforma-border bg-surface-muted px-3 py-3 text-xs text-platforma-subtle md:grid">
          <span>{t("settings.redesign.name")}</span><span>{t("settings.redesign.value")} / {t("settings.redesign.limit")}</span><span>{t("settings.redesign.period")}</span>
        </div>
        <div className="divide-y divide-platforma-border">
          {(entitlements.data || []).map(item => {
            const percent = item.limit && item.limit > 0 ? Math.min(100, Math.round((item.value / item.limit) * 100)) : item.value > 0 ? 100 : 0;
            const reached = item.limit !== null && item.value >= item.limit;
            return <div key={item.metric} className="grid gap-3 px-3 py-4 text-sm md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,0.8fr)] md:gap-4">
              <p className="font-semibold">{formatMetric(item.metric, t)}</p>
              <div>
                <p className="tabular-nums">{item.value.toLocaleString(locale, { maximumFractionDigits: 2 })}<span className="text-platforma-subtle"> / {item.limit === null ? t("settings.unlimited") : item.limit.toLocaleString(locale)}</span></p>
                {item.limit !== null && <div role="progressbar" aria-label={formatMetric(item.metric, t)} aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent} className="mt-2 h-1.5 overflow-hidden rounded-full bg-surface-muted"><div className={"h-full rounded-full " + (reached ? "bg-platforma-warning" : "bg-brand-500")} style={{ width: percent + "%" }} /></div>}
                {reached && <p className="mt-2 text-xs text-platforma-warning">{t("settings.limitReached")}</p>}
                {"remaining" in item && item.remaining !== null && <p className="mt-1 text-xs text-platforma-subtle">{t("settings.remaining", { count: item.remaining })}</p>}
              </div>
              <p className="text-xs text-platforma-subtle">{item.period_kind === "month" && item.period_start ? t("settings.usageMonth", { month: new Date(item.period_start).toLocaleDateString(locale, { month: "long", year: "numeric", timeZone: "UTC" }) }) : t("settings.usageCurrent")}</p>
            </div>;
          })}
          {!entitlements.data?.length && <p className="py-8 text-sm text-platforma-subtle">{t("settings.noUsage")}</p>}
        </div>
      </>}
    </div>
  </SettingsSection>;
}

import { CheckSquare, Tag, Layers, MessageSquare, Settings, ShieldAlert, Wallet } from "lucide-react";
import type { PersonalFeedFilters } from "../../api/notifications";
import { Select } from "../../components/ui/Select";
import { useI18n } from "../../lib/i18n";

export type FeedView = "all" | "unread" | "awaiting";
export const notificationCategories = [
  { value: "tasks", key: "tasks", icon: CheckSquare },
  { value: "sales", key: "sales", icon: Tag },
  { value: "outreach", key: "outreach", icon: MessageSquare },
  { value: "finance", key: "finance", icon: Wallet },
  { value: "ai_alerts", key: "aiAlerts", icon: ShieldAlert },
  { value: "system", key: "system", icon: Settings },
] as const;

export function NotificationFilters({ view, filters, unread, onView, onFilters }: {
  view: FeedView;
  filters: PersonalFeedFilters;
  unread?: number;
  onView: (value: FeedView) => void;
  onFilters: (value: PersonalFeedFilters) => void;
}) {
  const { t } = useI18n();
  const rowClass = "platforma-focus-ring flex min-h-11 w-full items-center gap-3 rounded-control px-3 py-2 text-left text-sm hover:bg-surface-hover";
  return <div className="space-y-5" data-testid="notification-filters">
    <div className="space-y-1" role="group" aria-label={t("notification.filters")}>
      {(["all", "unread", "awaiting"] as const).map(value => <button type="button" key={value} aria-pressed={view === value}
        className={`${rowClass} ${view === value ? "bg-brand-50 font-semibold text-brand-700" : "text-platforma-ink"}`} onClick={() => onView(value)}>
        <span className="min-w-0 flex-1">{t(`notification.filter.${value}`)}</span>
        {value === "unread" && unread !== undefined ? <span className="tabular-nums">{unread}</span> : null}
      </button>)}
    </div>
    <div className="border-t border-platforma-border pt-4" role="group" aria-label={t("notification.categories")}>
      <h2 className="mb-2 px-3 text-xs font-semibold text-platforma-subtle">{t("notification.categories")}</h2>
      <button type="button" aria-pressed={!filters.category} className={`${rowClass} ${!filters.category ? "bg-surface-muted font-semibold" : ""}`}
        onClick={() => onFilters({ ...filters, category: undefined })}><Layers size={18} aria-hidden="true" />{t("notification.filter.all")}</button>
      {notificationCategories.map(({ value, key, icon: Icon }) => <button type="button" key={value} aria-pressed={filters.category === value}
        className={`${rowClass} ${filters.category === value ? "bg-brand-50 font-semibold text-brand-700" : "text-platforma-ink"}`}
        onClick={() => onFilters({ ...filters, category: filters.category === value ? undefined : value })}>
        <Icon size={18} aria-hidden="true" />{t(`notification.category.${key}`)}
      </button>)}
    </div>
    <div className="border-t border-platforma-border pt-4">
      <Select label={t("notification.period")} value={filters.period || "all"}
        onChange={event => onFilters({ ...filters, period: event.target.value as PersonalFeedFilters["period"] })}
        options={["all", "7d", "30d"].map(value => ({ value, label: t(`notification.period.${value}`) }))} />
    </div>
  </div>;
}

import { CalendarDays, DoorOpen, GitBranch, List, Users } from "lucide-react";
import type { ReactNode } from "react";
import { NavLink, useNavigate, useSearchParams } from "react-router";
import { Select } from "../../components/ui/Select";
import { cn } from "../../lib/cn";
import { useI18n } from "../../lib/i18n";
import "./management.css";

export type ManagementSection = "services" | "staff" | "resources" | "branches" | "working-hours";
export const managementSections = [
  { id: "services", key: "nav.services", icon: List },
  { id: "staff", key: "management.specialists", icon: Users },
  { id: "resources", key: "management.rooms", icon: DoorOpen },
  { id: "branches", key: "branches.title", icon: GitBranch },
  { id: "working-hours", key: "nav.workingHours", icon: CalendarDays },
] as const;

export function ManagementLayout({ section, children }: { section: ManagementSection; children: ReactNode }) {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const branch = params.get("branch");
  const destination = (id: string) => `/app/business/${id}${branch ? `?branch=${encodeURIComponent(branch)}` : ""}`;
  return <div className="management-layout grid min-w-0 gap-5 py-4 lg:grid-cols-[190px_minmax(0,1fr)] lg:gap-7" data-testid="management-workspace">
    <aside className="hidden border-r border-platforma-border pr-4 lg:block">
      <nav aria-label={t("business.navigationLabel")} className="sticky top-20 space-y-1">
        {managementSections.map(({ id, key, icon: Icon }) => <NavLink key={id} to={destination(id)}
          className={({ isActive }) => cn("platforma-focus-ring flex min-h-11 items-center gap-3 rounded-control px-3 py-3 text-sm font-medium",
            isActive ? "bg-brand-50 text-brand-700" : "text-platforma-subtle hover:bg-surface-hover hover:text-platforma-text")}>
          <Icon size={18} aria-hidden="true" className="shrink-0" /><span>{t(key)}</span>
        </NavLink>)}
      </nav>
    </aside>
    <div className="management-main min-w-0">
      <div className="mb-5 lg:hidden"><Select label={t("management.section")} value={section}
        options={managementSections.map(item => ({ value: item.id, label: t(item.key) }))}
        onChange={event => navigate(destination(event.target.value))} /></div>
      {children}
    </div>
  </div>;
}

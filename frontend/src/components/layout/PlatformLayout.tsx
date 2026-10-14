import { BarChart3, CreditCard, FileText, Activity, LayoutDashboard, LogOut, Settings, ShieldCheck, Store, Target } from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router";
import { useAuth } from "../../features/auth/AuthProvider";
import { cn } from "../../lib/cn";
import { useI18n } from "../../lib/i18n";
import { Button } from "../ui/Button";
import { LanguageSelector } from "./LanguageSelector";

const platformNav = [
  { to: "/platform", label: "platform.nav.overview", icon: LayoutDashboard, end: true },
  { to: "/platform/operations", label: "platform.nav.operations", icon: Activity },
  { to: "/platform/merchants", label: "platform.nav.merchants", icon: Store },
  { to: "/platform/prospects", label: "platform.nav.prospects", icon: Target },
  { to: "/platform/landings", label: "platform.nav.landings", icon: FileText },
  { to: "/platform/billing", label: "platform.nav.billing", icon: CreditCard },
  { to: "/platform/analytics", label: "platform.nav.analytics", icon: BarChart3 },
  { to: "/platform/settings", label: "platform.nav.settings", icon: Settings },
];

export function PlatformLayout() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { t } = useI18n();
  const navigation = (mobile = false) => platformNav.map(item => {
    const Icon = item.icon;
    return <NavLink key={item.to} to={item.to} end={item.end}
      className={({ isActive }) => cn("platforma-focus-ring flex min-h-11 items-center gap-2.5 rounded-control px-3 py-2 text-sm font-medium text-platforma-subtle transition hover:bg-surface-hover hover:text-platforma-text",
        mobile && "shrink-0", isActive && "bg-brand-50 text-platforma-text ring-1 ring-brand-100")}>
      <Icon size={18} aria-hidden="true" /><span>{t(item.label)}</span>
    </NavLink>;
  });
  return <div className="min-h-dvh bg-surface text-platforma-text">
    <aside className="fixed inset-y-0 left-0 hidden w-56 flex-col border-r border-platforma-border bg-surface-card lg:flex">
      <NavLink to="/platform" className="platforma-focus-ring flex h-14 items-center gap-2.5 border-b border-platforma-border px-4 font-semibold">
        <ShieldCheck size={22} className="text-brand-600" aria-hidden="true" />PlatformaCRM
      </NavLink>
      <nav aria-label={t("platform.title")} className="min-h-0 flex-1 space-y-1 overflow-y-auto p-3">{navigation()}</nav>
    </aside>
    <div className="min-w-0 lg:pl-56">
      <header className="sticky top-0 z-40 flex min-h-14 flex-wrap items-center justify-between gap-2 border-b border-platforma-border bg-surface-card px-3 py-2 sm:px-5">
        <span className="text-sm font-semibold text-platforma-subtle">{t("platform.title")}</span>
        <div className="flex min-w-0 items-center gap-2">
          <span className="hidden max-w-64 truncate text-sm text-platforma-subtle md:block">{user?.email}</span>
          <LanguageSelector />
          <Button variant="ghost" onClick={() => { logout(); navigate("/login"); }} aria-label={t("header.logout")}>
            <LogOut size={17} aria-hidden="true" /><span className="hidden sm:inline">{t("header.logout")}</span>
          </Button>
        </div>
      </header>
      <nav aria-label={t("platform.title")} className="flex gap-1 overflow-x-auto border-b border-platforma-border bg-surface-card p-2 lg:hidden">{navigation(true)}</nav>
      <main data-workspace-content className="mx-auto min-w-0 max-w-[1600px] p-3 sm:p-5"><Outlet /></main>
    </div>
  </div>;
}

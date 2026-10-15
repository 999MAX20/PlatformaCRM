import { Activity, LayoutDashboard, LifeBuoy, LogOut, Settings2, ShieldCheck, Store, UserRound } from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router";
import { useAuth } from "../../features/auth/AuthProvider";
import { cn } from "../../lib/cn";
import { useI18n } from "../../lib/i18n";
import { ActionMenu } from "../ui/ActionMenu";
import { PlatformHeadingContext, type PlatformHeading } from "./PlatformPageHeading";

const platformNav = [
  { to: "/platform", label: "platform.nav.overview", icon: LayoutDashboard, end: true },
  { to: "/platform/merchants", label: "platform.nav.merchants", icon: Store },
  { to: "/platform/support", label: "supportCases.title", icon: LifeBuoy },
  { to: "/platform/operations", label: "platform.nav.operations", icon: Activity },
];
function routeTitle(path: string) {
  path = path.replace(/\/+$/, "");
  if (path === "/platform/account") return "platform.shell.account";
  if (/\/incidents\//.test(path)) return "supportIncidents.open";
  if (/^\/platform\/merchants\/[^/]+/.test(path)) return "supportCases.clinic";
  if (/^\/platform\/support\/[^/]+/.test(path)) return "platform.shell.case";
  return platformNav.find(item => item.to === path)?.label || "platform.title";
}
export function PlatformLayout() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const { user, logout } = useAuth();
  const { t } = useI18n();
  const [heading, setHeading] = useState<PlatformHeading | null>(null);
  const [hovered, setHovered] = useState(false);
  const [keyboardFocus, setKeyboardFocus] = useState(false);
  const expanded = hovered || keyboardFocus;
  const title = heading?.path === pathname ? heading.title : t(routeTitle(pathname));
  const navigation = (mobile = false) => platformNav.map(item => {
    const Icon = item.icon;
    return <NavLink key={item.to} to={item.to} end={item.end} aria-label={t(item.label)} title={t(item.label)}
      className={({ isActive }) => cn("platforma-focus-ring flex min-h-11 items-center gap-3 rounded-control px-3 py-2 text-sm font-medium text-platforma-subtle transition hover:bg-surface-hover hover:text-platforma-text",
        mobile && "shrink-0", isActive && "bg-brand-50 text-platforma-text ring-1 ring-brand-100")}>
      <Icon size={20} className="shrink-0" aria-hidden="true" /><span className={cn("whitespace-nowrap", !mobile && !expanded && "sr-only")}>{t(item.label)}</span>
    </NavLink>;
  });
  return <PlatformHeadingContext.Provider value={setHeading}>
    <div className="min-h-dvh bg-surface text-platforma-text [--account-content-width:min(960px,calc(100vw_-_2rem))] lg:[--account-content-width:min(960px,calc(100vw_-_7rem))]">
      <aside data-testid="platform-sidebar" onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)}
        onPointerDown={() => setKeyboardFocus(false)} onKeyDown={event => { if (event.key === "Tab") setKeyboardFocus(true); }}
        onFocus={event => { if (event.target.matches(":focus-visible")) setKeyboardFocus(true); }}
        onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget)) setKeyboardFocus(false); }}
        className={cn("fixed inset-y-0 left-0 z-50 hidden flex-col border-r border-platforma-border bg-surface-card transition-[width] duration-200 motion-reduce:transition-none lg:flex", expanded ? "w-56 shadow-lg" : "w-16")}>
        <NavLink to="/platform" aria-label="PlatformaCRM" className="platforma-focus-ring flex h-[57px] shrink-0 items-center gap-3 overflow-hidden border-b border-platforma-border px-5 font-semibold">
          <ShieldCheck size={22} className="shrink-0 text-brand-600" aria-hidden="true" /><span className={cn("whitespace-nowrap", !expanded && "sr-only")}>PlatformaCRM</span>
        </NavLink>
        <nav aria-label={t("platform.title")} className="min-h-0 flex-1 space-y-1 overflow-x-hidden overflow-y-auto px-2 py-3">{navigation()}</nav>
      </aside>
      <div className="min-w-0 lg:pl-16">
        <header className="sticky top-0 z-40 flex h-[57px] items-center justify-between gap-3 border-b border-platforma-border bg-surface-card px-4 lg:px-6">
          <h1 title={title} className="min-w-0 truncate text-lg font-semibold">{title}</h1>
          <ActionMenu label={`${t("platform.shell.account")}${user?.email ? `: ${user.email}` : ""}`}
            triggerClassName="max-w-[50%] shrink-0"
            triggerContent={<><span title={user?.email} className="hidden max-w-64 truncate text-sm font-normal text-platforma-subtle sm:block">{user?.email}</span><UserRound size={20} className="shrink-0" aria-hidden="true" /></>}
            items={[
              { key: "profile", label: t("account.profileEyebrow"), icon: UserRound, onSelect: () => navigate("/platform/account#profile") },
              { key: "security", label: t("account.loginHistoryEyebrow"), icon: ShieldCheck, onSelect: () => navigate("/platform/account#security") },
              { key: "interface", label: t("account.interfaceTitle"), icon: Settings2, onSelect: () => navigate("/platform/account#interface") },
              { key: "logout", label: t("header.logout"), icon: LogOut, separatorBefore: true, onSelect: () => { logout(); navigate("/login"); } },
            ]} />
        </header>
        <nav aria-label={t("platform.title")} className="flex gap-1 overflow-x-auto border-b border-platforma-border bg-surface-card p-2 lg:hidden">{navigation(true)}</nav>
        <main data-workspace-content className="mx-auto min-w-0 max-w-[1600px] p-4 lg:p-6"><Outlet /></main>
      </div>
    </div>
  </PlatformHeadingContext.Provider>;
}

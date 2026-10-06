import {
  BarChart3,
  Building2,
  CalendarDays,
  Bot,
  ChevronDown,
  Clock3,
  Home,
  Inbox,
  KanbanSquare,
  ListChecks,
  MessageSquareText,
  PlugZap,
  Settings,
  Users,
} from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLayoutEffect, useMemo, useRef, useState } from "react";
import { Link, NavLink, useLocation } from "react-router";

import platformaCrmLogo from "../../assets/platforma-crm-logo.png";
import { useAuth } from "../../features/auth/AuthProvider";
import { inboxApi } from "../../api/inbox";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { cn } from "../../lib/cn";
import { useI18n } from "../../lib/i18n";
import { hasPermission } from "../../lib/permissions";
import { prefetchRouteData } from "../../lib/prefetch";
import { realtimeIntervals, realtimeQueryOptions } from "../../lib/realtime";

type SidebarItem = {
  to?: string;
  label: string;
  icon: typeof Home;
  resource?: string;
  action?: string;
  children?: SidebarItem[];
};

type SidebarSection = {
  id: string;
  titleKey: string;
  items: SidebarItem[];
};

const desktopSections = [
  {
    id: "work",
    titleKey: "nav.workspace",
    items: [
      { to: "/app/dashboard", label: "nav.dashboard", icon: Home },
      { to: "/app/leads", label: "nav.leads", icon: Inbox, resource: "leads" },
      { to: "/app/deals", label: "nav.deals", icon: KanbanSquare, resource: "deals" },
      { to: "/app/clients", label: "nav.clients", icon: Users, resource: "clients" },
      { to: "/app/tasks", label: "nav.tasks", icon: ListChecks, resource: "tasks" },
      { to: "/app/calendar", label: "nav.calendar", icon: CalendarDays, resource: "appointments" },
      { to: "/app/conversations", label: "nav.conversations", icon: MessageSquareText, resource: "conversations" },
      { to: "/app/ai-agents", label: "nav.aiAgents", icon: Bot, resource: "ai_automation" },
      {
        label: "nav.channels",
        icon: PlugZap,
        children: [
          { to: "/app/integrations", label: "nav.integrations", icon: PlugZap, resource: "integrations" },
        ],
      },
      { to: "/app/business", label: "nav.business", icon: Building2, resource: "settings" },
      {
        label: "nav.control",
        icon: BarChart3,
        children: [
          { to: "/app/analytics", label: "nav.analytics", icon: BarChart3, resource: "analytics" },
          { to: "/app/timeline", label: "nav.timeline", icon: Clock3, resource: "analytics" },
        ],
      },
      { to: "/app/settings", label: "nav.settings", icon: Settings, resource: "settings", action: "update" },
    ],
  },
] satisfies SidebarSection[];

const mobileDrawerSections = [
  {
    id: "operations",
    titleKey: "nav.operations",
    items: [
      { to: "/app/dashboard", label: "nav.dashboard", icon: Home },
      { to: "/app/leads", label: "nav.leads", icon: Inbox, resource: "leads" },
      { to: "/app/deals", label: "nav.deals", icon: KanbanSquare, resource: "deals" },
      { to: "/app/clients", label: "nav.clients", icon: Users, resource: "clients" },
      { to: "/app/tasks", label: "nav.tasks", icon: ListChecks, resource: "tasks" },
      { to: "/app/calendar", label: "nav.calendar", icon: CalendarDays, resource: "appointments" },
      { to: "/app/conversations", label: "nav.conversations", icon: MessageSquareText, resource: "conversations" },
      { to: "/app/ai-agents", label: "nav.aiAgents", icon: Bot, resource: "ai_automation" },
      {
        label: "nav.channels",
        icon: PlugZap,
        children: [
          { to: "/app/integrations", label: "nav.integrations", icon: PlugZap, resource: "integrations" },
        ],
      },
      { to: "/app/business", label: "nav.business", icon: Building2, resource: "settings" },
      {
        label: "nav.control",
        icon: BarChart3,
        children: [
          { to: "/app/analytics", label: "nav.analytics", icon: BarChart3, resource: "analytics" },
          { to: "/app/timeline", label: "nav.timeline", icon: Clock3, resource: "analytics" },
        ],
      },
      { to: "/app/settings", label: "nav.settings", icon: Settings, resource: "settings", action: "update" },
    ],
  },
] satisfies SidebarSection[];

function isItemActive(pathname: string, to?: string) {
  if (!to) return false;
  return pathname === to || pathname.startsWith(`${to}/`);
}

function isSidebarItemVisible(item: SidebarItem, user: ReturnType<typeof useAuth>["user"], businessId?: number): boolean {
  if (item.to === "/app/ai-agents") return ["ai_automation", "ai_assistant", "ai_analyst"].some(resource => hasPermission(user, businessId, resource, "view"));
  if (item.resource && !hasPermission(user, businessId, item.resource, item.action)) return false;
  if (!item.children?.length) return true;
  return item.children.some((child) => isSidebarItemVisible(child, user, businessId));
}

function filterSidebarItem(item: SidebarItem, user: ReturnType<typeof useAuth>["user"], businessId?: number): SidebarItem | null {
  if (!isSidebarItemVisible(item, user, businessId)) return null;
  if (!item.children?.length) return item;
  const children = item.children.map((child) => filterSidebarItem(child, user, businessId)).filter(Boolean) as SidebarItem[];
  return children.length ? { ...item, children } : null;
}

export function Sidebar({
  expanded = false,
  forceVisible = false,
  mobileDrawer = false,
  onDesktopMouseEnter,
  onDesktopMouseLeave,
  onNavigate,
}: {
  expanded?: boolean;
  forceVisible?: boolean;
  mobileDrawer?: boolean;
  onDesktopMouseEnter?: () => void;
  onDesktopMouseLeave?: () => void;
  onNavigate?: () => void;
}) {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const location = useLocation();
  const { user } = useAuth();
  const { business } = useActiveBusiness();
  const inboxSummary = useQuery({
    queryKey: ["inbox-summary", business?.id],
    queryFn: inboxApi.getSummary,
    enabled: Boolean(user) && Boolean(business?.id) && hasPermission(user, business?.id, "conversations"),
    refetchInterval: realtimeIntervals.inboxConversationsMs,
    ...realtimeQueryOptions,
  });
  const unreadMessages = inboxSummary.data?.unread_messages ?? inboxSummary.data?.unread ?? 0;
  const isExpanded = forceVisible || expanded;
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({ "nav.channels": true, "nav.control": true });
  const scrollRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const [canScrollDown, setCanScrollDown] = useState(false);

  useLayoutEffect(() => {
    const viewport = scrollRef.current;
    const content = contentRef.current;
    if (!viewport || !content) return;

    const updateScrollHint = () => setCanScrollDown(
      viewport.clientHeight > 0 && viewport.scrollHeight - viewport.clientHeight - viewport.scrollTop > 1,
    );
    const observer = new ResizeObserver(updateScrollHint);
    observer.observe(viewport);
    observer.observe(content);
    viewport.addEventListener("scroll", updateScrollHint, { passive: true });
    updateScrollHint();
    return () => {
      observer.disconnect();
      viewport.removeEventListener("scroll", updateScrollHint);
    };
  }, []);

  const visibleGroups = useMemo(
    () =>
      (mobileDrawer ? mobileDrawerSections : desktopSections)
        .map((group) => ({
          ...group,
          items: group.items.map((item) => filterSidebarItem(item, user, business?.id)).filter(Boolean) as SidebarItem[],
        }))
        .filter((group) => group.items.length),
    [business?.id, mobileDrawer, user],
  );
  return (
    <aside
      data-testid={forceVisible ? "mobile-sidebar" : "desktop-sidebar"}
      onMouseEnter={forceVisible ? undefined : onDesktopMouseEnter}
      onMouseLeave={forceVisible ? undefined : onDesktopMouseLeave}
      className={cn(
        "relative z-[60] shrink-0 border-r border-platforma-border bg-surface-card transition-[width,box-shadow,background-color,backdrop-filter] duration-200 ease-out",
        forceVisible && "h-dvh max-h-dvh w-[min(360px,94vw)] bg-surface-card shadow-premium backdrop-blur-2xl",
        !forceVisible && cn(
          "hidden bg-surface-card/[0.92] backdrop-blur-2xl lg:fixed lg:inset-y-0 lg:left-0 lg:block",
          isExpanded ? "lg:w-[224px] lg:bg-surface-card lg:shadow-panel lg:backdrop-blur-2xl" : "lg:w-16",
        ),
        !forceVisible && "hidden lg:block",
      )}
    >
      <div className="flex h-full min-h-0 flex-col pb-[max(4.5rem,env(safe-area-inset-bottom))]">
        <div className={cn("flex h-[4.5rem] shrink-0 items-center justify-center", mobileDrawer && "pr-16")}>
          <Link
            to="/app/dashboard"
            onClick={onNavigate}
            aria-label="PlatformaCRM"
            className={cn("platforma-focus-ring flex items-center justify-center overflow-hidden rounded-control", isExpanded ? "w-[184px] max-w-full" : "h-10 w-8")}
          >
            {isExpanded ? (
              <img src={platformaCrmLogo} alt="" width={4096} height={1366} className="block h-auto w-full" />
            ) : (
              <svg viewBox="64 288 416 512" className="h-10 w-8" aria-hidden="true">
                <image href={platformaCrmLogo} width="4096" height="1366" />
              </svg>
            )}
          </Link>
        </div>
        <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto px-1.5 no-scrollbar">
          <div ref={contentRef} className="space-y-2">
          {visibleGroups.map((group) => {
            return (
            <section key={group.id}>
              {mobileDrawer ? <div
                className="mb-1 flex min-h-7 w-full items-center justify-between rounded-control px-3 text-left text-[10px] font-semibold text-platforma-faint transition-colors hover:bg-surface-hover hover:text-platforma-subtle"
              >
                <span>{t(group.titleKey)}</span>
              </div> : null}

              <nav className="space-y-0.5">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  const childActive = item.children?.some((child) => isItemActive(location.pathname, child.to)) || false;
                  const active = isItemActive(location.pathname, item.to) || childActive;
                  const hasChildren = Boolean(item.children?.length);
                  const childrenOpen = Boolean(openGroups[item.label] || childActive);

                  if (hasChildren) {
                    return (
                      <div key={item.label}>
                        <button
                          type="button"
                          onClick={() => setOpenGroups((value) => ({ ...value, [item.label]: !childrenOpen }))}
                          title={t(item.label)}
                          className={cn(
                            "platforma-focus-ring group relative flex min-h-10 w-full items-center gap-2 rounded-control border-l-2 border-transparent px-3 py-2 text-xs font-semibold text-platforma-subtle transition-colors duration-150",
                            !isExpanded && "justify-center px-0",
                            "hover:bg-brand-50 hover:text-platforma-text",
                            active && "border-[var(--platforma-brand-content)] bg-brand-50 text-platforma-text",
                          )}
                        >
                          <span
                            className={cn(
                              "grid h-5 w-5 shrink-0 place-items-center text-platforma-faint transition-colors",
                              active && "text-brand-700",
                              !active && "group-hover:text-platforma-text",
                            )}
                          >
                            <Icon size={18} strokeWidth={2.1} />
                          </span>
                          <span className={cn("min-w-0 truncate text-left transition-opacity duration-150", isExpanded ? "opacity-100" : "hidden opacity-0")}>{t(item.label)}</span>
                          {!isExpanded ? <span className="sr-only">{t(item.label)}</span> : null}
                          {isExpanded ? <ChevronDown size={16} className={cn("ml-auto text-platforma-faint transition-transform", childrenOpen && "rotate-180")} /> : null}
                        </button>
                        {isExpanded && childrenOpen ? (
                          <div className="ml-6 mt-1 space-y-0.5 border-l border-platforma-border pl-2">
                            {item.children?.map((child) => {
                              const ChildIcon = child.icon;
                              const childIsActive = isItemActive(location.pathname, child.to);
                              return child.to ? (
                                <NavLink
                                  key={child.to}
                                  to={child.to}
                                  onClick={onNavigate}
                                  onMouseEnter={() => prefetchRouteData(child.to!, queryClient, business?.id)}
                                  onFocus={() => prefetchRouteData(child.to!, queryClient, business?.id)}
                                  title={t(child.label)}
                                  className={cn(
                                    "platforma-focus-ring group relative flex min-h-9 items-center gap-2 rounded-control px-2.5 py-1.5 text-xs font-semibold text-platforma-subtle transition-colors duration-150",
                                    "hover:bg-brand-50 hover:text-platforma-text",
                                    childIsActive && "bg-brand-50 text-platforma-text ring-1 ring-brand-100",
                                  )}
                                >
                                  <ChildIcon size={16} strokeWidth={2.1} className={cn("shrink-0 text-platforma-faint", childIsActive && "text-brand-700")} />
                                  <span className="min-w-0 truncate">{t(child.label)}</span>
                                </NavLink>
                              ) : null;
                            })}
                          </div>
                        ) : null}
                      </div>
                    );
                  }

                  return (
                    <NavLink
                      key={item.to}
                      to={item.to!}
                      end={item.to === "/app/dashboard"}
                      onClick={onNavigate}
                      onMouseEnter={() => prefetchRouteData(item.to!, queryClient, business?.id)}
                      onFocus={() => prefetchRouteData(item.to!, queryClient, business?.id)}
                      title={t(item.label)}
                      className={cn(
                        "platforma-focus-ring group relative flex min-h-10 items-center gap-2 rounded-control border-l-2 border-transparent px-3 py-2 text-xs font-semibold text-platforma-subtle transition-colors duration-150",
                        !isExpanded && "justify-center px-0",
                        "hover:bg-brand-50 hover:text-platforma-text",
                        active && "border-[var(--platforma-brand-content)] bg-brand-50 text-platforma-text",
                      )}
                    >
                      <span
                        className={cn(
                          "grid h-5 w-5 shrink-0 place-items-center text-platforma-faint transition-colors",
                          active && "text-brand-700",
                          !active && "group-hover:text-platforma-text",
                        )}
                      >
                        <Icon size={18} strokeWidth={2.1} />
                      </span>
                      <span className={cn("min-w-0 truncate transition-opacity duration-150", isExpanded ? "opacity-100" : "hidden opacity-0")}>{t(item.label)}</span>
                      {!isExpanded ? <span className="sr-only">{t(item.label)}</span> : null}
                      {item.to === "/app/conversations" && unreadMessages ? (
                        <span className={cn("min-w-5 rounded-full bg-platforma-danger px-1.5 py-0.5 text-center text-[10px] font-semibold leading-none text-white shadow-xs", isExpanded ? "ml-auto" : "absolute right-1 top-1 px-1")}>
                          {unreadMessages > 99 ? "99+" : unreadMessages}
                        </span>
                      ) : active && isExpanded ? <span className="ml-auto h-2 w-2 rounded-full bg-[var(--platforma-brand-content)]" /> : null}
                    </NavLink>
                  );
                })}
              </nav>
            </section>
            );
          })}

          </div>
        </div>
        {canScrollDown ? (
          <div aria-hidden="true" data-testid="sidebar-scroll-hint" className="pointer-events-none absolute inset-x-0 bottom-[max(4.5rem,env(safe-area-inset-bottom))] flex h-8 translate-y-full items-center justify-center text-platforma-subtle">
            <ChevronDown size={20} strokeWidth={2} />
          </div>
        ) : null}
      </div>
    </aside>
  );
}

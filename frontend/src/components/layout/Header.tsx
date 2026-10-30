import { NotificationBell } from "./NotificationBell";
import { getRouteTitle } from "../../app/routeMetadata";

import { InboxNotificationEffects } from "./InboxNotificationEffects";
import { Menu, SlidersHorizontal, X } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import { useLocation } from "react-router";

import { useAuth } from "../../features/auth/AuthProvider";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useI18n } from "../../lib/i18n";

import { Button } from "../ui/Button";
import { Drawer } from "../ui/Overlay";

import { GlobalSearch } from "./GlobalSearch";
import { HeaderAccountLink } from "./HeaderAccountLink";
import { mobileNavigationDrawerId } from "./MobileNav";
import type { PageHeaderConfig } from "./PageHeaderContext";

export function Header({
  menuOpen,
  onMenuClick,
  pageHeader,
}: {
  menuOpen: boolean;
  onMenuClick: () => void;
  pageHeader: PageHeaderConfig | null;
}) {
  const location = useLocation();

  const { user } = useAuth();
  const { business } = useActiveBusiness();
  const { t } = useI18n();

  const [showNotifications, setShowNotifications] = useState(false);
  const [showFilters, setShowFilters] = useState(false);

  const [headerVisible, setHeaderVisible] = useState(true);

  const lastScrollYRef = useRef(0);
  const filterDrawerId = useId();
  const filterDrawerTitleId = useId();

  const activeMembership = user?.memberships?.find(
    (membership) =>
      String(membership.business) === String(business?.id) &&
      membership.is_active,
  );

  const currentPageTitle =
    pageHeader?.title || getRouteTitle(location.pathname, t);

  useEffect(() => {
    lastScrollYRef.current = window.scrollY;

    function handleScroll() {
      const currentY = window.scrollY;
      const delta = currentY - lastScrollYRef.current;

      if (currentY < 24 || showNotifications) {
        setHeaderVisible(true);
        lastScrollYRef.current = currentY;
        return;
      }

      if (Math.abs(delta) < 8) return;
      setHeaderVisible(delta < 0 || currentY < 80);
      lastScrollYRef.current = currentY;
    }

    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, [showNotifications]);

  return (
    <header
      className={`fixed left-0 right-0 top-0 z-50 border-b border-platforma-border bg-surface/[0.92] shadow-soft backdrop-blur-xl transition-transform duration-200 ease-out lg:left-16 ${headerVisible ? "translate-y-0" : "-translate-y-full"}`}
    >
      <InboxNotificationEffects
        user={user}
        business={business}
        activeMembership={activeMembership}
      />
      <div className="grid h-14 grid-cols-[auto_1fr_auto] items-center gap-3 px-3 sm:px-5 lg:grid-cols-[220px_var(--global-search-width)_minmax(0,1fr)]">
        <div className="flex min-w-0 items-center gap-2 sm:gap-3">
          <Button
            className="h-10 w-10 min-h-10 min-w-10 px-0 text-platforma-ink lg:hidden"
            variant="ghost"
            onClick={onMenuClick}
            aria-label={t("sidebar.expand")}
            aria-controls={mobileNavigationDrawerId}
            aria-expanded={menuOpen}
            data-testid="header-mobile-menu-trigger"
          >
            <Menu aria-hidden="true" size={22} strokeWidth={2.2} />
          </Button>
          <div className="hidden min-w-0 items-center gap-4 lg:flex">
            <span className="max-w-[220px] truncate text-[21px] font-semibold leading-7 text-platforma-text">
              {currentPageTitle}
            </span>
          </div>
          <div
            className={pageHeader ? "min-w-0 flex-1 lg:hidden" : "lg:hidden"}
          >
            <GlobalSearch />
          </div>
        </div>

        <div className="hidden min-w-0 justify-self-center lg:block lg:w-full">
          <GlobalSearch />
        </div>

        <div className="flex min-w-0 items-center justify-end gap-1.5 sm:gap-2">
          {pageHeader ? (
            <div className="hidden min-w-0 items-center justify-end gap-2 lg:flex">
              {pageHeader.filters ? (
                <div className="relative">
                  <Button
                    variant={
                      pageHeader.activeFilterCount ? "primary" : "secondary"
                    }
                    className="relative h-9 shrink-0 px-3"
                    onClick={() => setShowFilters((current) => !current)}
                    aria-label={pageHeader.filterLabel || t("calendar.filters")}
                    aria-expanded={showFilters}
                    aria-controls={filterDrawerId}
                    data-testid="header-filter-trigger"
                  >
                    <SlidersHorizontal size={17} />
                    <span className="hidden xl:inline">
                      {pageHeader.filterLabel || t("calendar.filters")}
                    </span>
                    {pageHeader.activeFilterCount ? (
                      <span className="grid min-w-5 place-items-center rounded-full bg-surface-card px-1.5 py-0.5 text-[11px] font-semibold text-brand-700">
                        {pageHeader.activeFilterCount}
                      </span>
                    ) : null}
                  </Button>
                  <Drawer
                    id={filterDrawerId}
                    open={showFilters}
                    onClose={() => setShowFilters(false)}
                    titleId={filterDrawerTitleId}
                    size="custom"
                    testId="header-filter-drawer"
                    backdropClassName="bg-platforma-ink/[0.28] backdrop-blur-[1px]"
                    className="max-w-[min(420px,calc(100vw-1rem))] rounded-none border-y-0 border-r-0 shadow-premium"
                  >
                    <div className="flex h-14 items-center justify-between gap-3 border-b border-platforma-border px-5">
                      <div
                        id={filterDrawerTitleId}
                        className="flex items-center gap-2 text-xs font-semibold text-platforma-subtle"
                      >
                        <SlidersHorizontal aria-hidden="true" size={15} />
                        <span>
                          {pageHeader.filterLabel || t("calendar.filters")}
                        </span>
                      </div>
                      <button
                        type="button"
                        className="platforma-focus-ring grid h-9 w-9 shrink-0 place-items-center rounded-control text-platforma-faint transition hover:bg-surface-hover hover:text-platforma-text"
                        onClick={() => setShowFilters(false)}
                        aria-label={t("common.close")}
                      >
                        <X aria-hidden="true" size={18} />
                      </button>
                    </div>
                    <div className="min-h-0 flex-1 overflow-y-auto p-5">
                      {pageHeader.filters}
                    </div>
                  </Drawer>
                </div>
              ) : null}
              {pageHeader.secondaryActions?.map((action, index) => {
                const Icon = action.icon;
                const showsLabel = action.presentation === "label";
                return (
                  <Button
                    key={action.label}
                    variant="secondary"
                    size={showsLabel ? "md" : "icon"}
                    className={
                      showsLabel ? "h-9 shrink-0 px-3" : "h-9 w-9 shrink-0"
                    }
                    onClick={action.onClick}
                    disabled={action.disabled}
                    title={action.title}
                    aria-label={action.label}
                    data-testid={`page-secondary-action-${index}`}
                    data-focus-return-id={action.focusReturnId}
                  >
                    {Icon ? <Icon size={17} /> : null}
                    {showsLabel ? (
                      <span className="hidden xl:inline">{action.label}</span>
                    ) : null}
                  </Button>
                );
              })}
              <PrimaryPageAction action={pageHeader.primaryAction} />
            </div>
          ) : null}
          {pageHeader?.secondaryActions?.map((action, index) => {
            if (!action.showOnMobile) return null;
            const Icon = action.icon;
            return (
              <Button
                key={action.label}
                variant="secondary"
                className="h-10 w-10 shrink-0 px-0 lg:hidden"
                onClick={action.onClick}
                disabled={action.disabled}
                title={action.title}
                aria-label={action.label}
                data-testid={`page-secondary-action-mobile-${index}`}
                data-focus-return-id={action.focusReturnId}
              >
                {Icon ? <Icon size={17} /> : null}
              </Button>
            );
          })}
          {pageHeader?.primaryAction ? (
            <div className="lg:hidden">
              <PrimaryPageAction action={pageHeader.primaryAction} compact />
            </div>
          ) : null}
          <NotificationBell
            user={user}
            business={business}
            showNotifications={showNotifications}
            setShowNotifications={setShowNotifications}
          />
          <HeaderAccountLink user={user} membership={activeMembership} />
        </div>
      </div>
      {pageHeader?.activeFilters ? (
        <div className="border-t border-platforma-border bg-surface/[0.92] px-4 py-1.5 sm:px-6">
          <div className="flex min-w-0 items-center gap-2 overflow-x-auto pb-1">
            {pageHeader.activeFilters}
          </div>
        </div>
      ) : null}
    </header>
  );
}

function PrimaryPageAction({
  action,
  compact = false,
}: {
  action?: PageHeaderConfig["primaryAction"];
  compact?: boolean;
}) {
  if (!action) return null;
  const Icon = action.icon;
  return (
    <Button
      data-testid="page-primary-action"
      variant={action.variant || "primary"}
      className={
        compact
          ? "h-10 w-10 shrink-0 px-0"
          : "h-9 shrink-0 whitespace-nowrap px-4"
      }
      onClick={action.onClick}
      disabled={action.disabled}
      title={action.title}
      aria-label={action.label}
    >
      {Icon ? <Icon size={17} /> : null}
      {compact ? null : action.label}
    </Button>
  );
}

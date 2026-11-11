import { NavLink, useSearchParams } from "react-router";

import { cn } from "../../../lib/cn";
import { useI18n } from "../../../lib/i18n";

const businessRoutes = [
  { to: "/app/business/company", labelKey: "business.company" },
  { to: "/app/business/branches", labelKey: "branches.title" },
  { to: "/app/business/staff", labelKey: "business.staff" },
  { to: "/app/business/services", labelKey: "nav.services" },
  { to: "/app/business/resources", labelKey: "branches.physicalResources" },
  { to: "/app/business/working-hours", labelKey: "nav.workingHours" },
];

export function BusinessWorkspaceNav() {
  const { t } = useI18n();
  const [params] = useSearchParams();
  const branch = params.get("branch");

  return (
    <nav
      aria-label={t("business.navigationLabel")}
      className="mb-3 shrink-0 overflow-x-auto rounded-card border border-platforma-border bg-surface-card p-1 shadow-card no-scrollbar"
    >
      <div className="flex min-w-max gap-1 sm:min-w-0">
        {businessRoutes.map((route) => (
          <NavLink
            key={route.to}
            to={{ pathname: route.to, search: branch ? `?branch=${encodeURIComponent(branch)}` : "" }}
            className={({ isActive }) => cn(
              "platforma-focus-ring inline-flex min-h-10 shrink-0 items-center justify-center rounded-control px-4 text-sm font-semibold transition sm:flex-1",
              isActive
                ? "bg-brand-50 text-brand-700 shadow-xs ring-1 ring-brand-100"
                : "text-platforma-subtle hover:bg-surface-hover hover:text-platforma-text",
            )}
          >
            {t(route.labelKey)}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}

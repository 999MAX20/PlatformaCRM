import { Navigate } from "react-router";

import { RouteErrorBoundary } from "../components/ui/RouteErrorBoundary";

import { PlatformRoute, PageLoader } from "./routeGuards";
import { PlatformLayout, AccountPage, PlatformOverviewPage, PlatformOperationsPage, PlatformMerchantsPage, PlatformMerchantDetailPage, SupportListPage, SupportDetailPage, SupportIncidentPage } from "./routeLoaders";
export const platformRoutes = [
{
    path: "/platform",
    errorElement: <RouteErrorBoundary />,
    element: (
      <PlatformRoute>
        <PageLoader>
          <PlatformLayout />
        </PageLoader>
      </PlatformRoute>
    ),
    children: [
      {
        index: true,
        element: (
          <PageLoader>
            <PlatformOverviewPage />
          </PageLoader>
        ),
      },
      {
        path: "operations",
        element: (
          <PageLoader>
            <PlatformOperationsPage />
          </PageLoader>
        ),
      },
      {
        path: "merchants",
        element: (
          <PageLoader>
            <PlatformMerchantsPage />
          </PageLoader>
        ),
      },
      {
        path: "merchants/:id",
        element: (
          <PageLoader>
            <PlatformMerchantDetailPage />
          </PageLoader>
        ),
      },
      { path: "account", element: <PageLoader><AccountPage platform /></PageLoader> },
      { path: "support", element: <PageLoader><SupportListPage platform /></PageLoader> },
      { path: "support/:id", element: <PageLoader><SupportDetailPage platform /></PageLoader> },
      { path: "merchants/:id/incidents/:component/:episode", element: <PageLoader><SupportIncidentPage /></PageLoader> },
      {
        path: "prospects",
        element: <Navigate to="/platform" replace />,
      },
      {
        path: "landings",
        element: <Navigate to="/platform" replace />,
      },
      {
        path: "billing",
        element: <Navigate to="/platform#finance" replace />,
      },
      {
        path: "analytics",
        element: <Navigate to="/platform" replace />,
      },
      {
        path: "settings",
        element: <Navigate to="/platform" replace />,
      },
    ],
  }
];

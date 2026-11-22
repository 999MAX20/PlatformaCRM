import { MerchantRoute, LayoutLoader, PageLoader, PermissionRoute, LegacyDashboardRedirect } from "./routeGuards";
import { AppLayout } from "./routeLoaders";
import { merchantFeatureRoutes } from "./merchantRoutes";
import { legacyMerchantRoutes } from "./legacyRoutes";
import { publicRoutes } from "./publicRoutes";
import { platformRoutes } from "./platformRoutes";
import { lazy } from "react";
import { RouterProvider, createBrowserRouter } from "react-router";

import { RouteErrorBoundary } from "../components/ui/RouteErrorBoundary";

import { NotFoundPage } from "../features/pilot/NotFoundPage";

const NotificationsPage = lazy(() => import("../features/notifications/NotificationsPage").then(module => ({ default: module.NotificationsPage })));
const ParticipationNotificationPage = lazy(() => import("../features/medical/ParticipationNotificationPage").then(module => ({ default: module.ParticipationNotificationPage })));

const merchantChildren: Array<(typeof merchantFeatureRoutes)[number] & { permissionAction?: string }> = [
  { path: "notifications", element: <PageLoader><NotificationsPage /></PageLoader> },
  { path: "medical/participations", element: <PageLoader><ParticipationNotificationPage /></PageLoader> },
  ...merchantFeatureRoutes];

const router = createBrowserRouter([
...publicRoutes,
...platformRoutes,
{
    path: "/app",
    errorElement: <RouteErrorBoundary />,
    element: (
      <MerchantRoute>
        <LayoutLoader>
          <AppLayout />
        </LayoutLoader>
      </MerchantRoute>
    ),
    children: merchantChildren.map(
      ({ resource, permissionAction, element, ...route }) => ({
        ...route,
        element: (
          <PermissionRoute resource={resource} action={permissionAction}>
            {element}
          </PermissionRoute>
        ),
      }),
    ),
  },
{
    path: "/dashboard/*",
    errorElement: <RouteErrorBoundary />,
    element: <LegacyDashboardRedirect />,
  },
...legacyMerchantRoutes.map((route) => ({
    path: route.path,
    errorElement: <RouteErrorBoundary />,
    element: (
      <MerchantRoute>
        <LayoutLoader>
          <AppLayout />
        </LayoutLoader>
      </MerchantRoute>
    ),
    children: [
      {
        index: true,
        element: (
          <PermissionRoute
            resource={route.resource}
            action={
              "permissionAction" in route ? route.permissionAction : undefined
            }
          >
            {route.element}
          </PermissionRoute>
        ),
      },
    ],
  })),
{
    path: "*",
    element: <NotFoundPage />,
    errorElement: <RouteErrorBoundary />,
  }
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}

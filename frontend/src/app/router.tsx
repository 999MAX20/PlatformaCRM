import { MerchantRoute, PageLoader, PermissionRoute, LegacyDashboardRedirect } from "./routeGuards";
import { AppLayout } from "./routeLoaders";
import { merchantFeatureRoutes } from "./merchantRoutes";
import { legacyMerchantRoutes } from "./legacyRoutes";
import { publicRoutes } from "./publicRoutes";
import { platformRoutes } from "./platformRoutes";
import { RouterProvider, createBrowserRouter } from "react-router";

import { RouteErrorBoundary } from "../components/ui/RouteErrorBoundary";

import { NotFoundPage } from "../features/pilot/NotFoundPage";


const merchantChildren: Array<(typeof merchantFeatureRoutes)[number] & { permissionAction?: string }> = [...merchantFeatureRoutes];

const router = createBrowserRouter([
...publicRoutes,
...platformRoutes,
{
    path: "/app",
    errorElement: <RouteErrorBoundary />,
    element: (
      <MerchantRoute>
        <PageLoader>
          <AppLayout />
        </PageLoader>
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
        <PageLoader>
          <AppLayout />
        </PageLoader>
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

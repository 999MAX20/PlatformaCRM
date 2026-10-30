import { Navigate } from "react-router";

import { RouteErrorBoundary } from "../components/ui/RouteErrorBoundary";

import { LoginPage } from "../features/auth/LoginPage";

import { PublicRoute, PageLoader } from "./routeGuards";
import { InviteAcceptPage, SignupPage, DocumentsPage, ForgotPasswordPage, ResetPasswordPage, AccountRecoveryPage, MfaPage } from "./routeLoaders";
export const publicRoutes = [
{ path: "/documents", element: <PageLoader><DocumentsPage /></PageLoader> },
{ path: "/documents/:documentId", element: <PageLoader><DocumentsPage /></PageLoader> },
{
    path: "/",
    errorElement: <RouteErrorBoundary />,
    element: (
      <PublicRoute>
        <LoginPage />
      </PublicRoute>
    ),
  },
{
    path: "/pricing",
    element: <Navigate to="/login" replace />,
    errorElement: <RouteErrorBoundary />,
  },
{
    path: "/bots",
    element: <Navigate to="/login" replace />,
    errorElement: <RouteErrorBoundary />,
  },
{
    path: "/crm",
    element: <Navigate to="/login" replace />,
    errorElement: <RouteErrorBoundary />,
  },
{
    path: "/contacts",
    element: <Navigate to="/login" replace />,
    errorElement: <RouteErrorBoundary />,
  },
{
    path: "/login",
    errorElement: <RouteErrorBoundary />,
    element: (
      <PublicRoute>
        <LoginPage />
      </PublicRoute>
    ),
  },
{
    path: "/signup",
    errorElement: <RouteErrorBoundary />,
    element: (
      <PublicRoute>
        <PageLoader>
          <SignupPage />
        </PageLoader>
      </PublicRoute>
    ),
  },
{
    path: "/mfa",
    errorElement: <RouteErrorBoundary />,
    element: (
      <PublicRoute>
        <PageLoader>
          <MfaPage />
        </PageLoader>
      </PublicRoute>
    ),
  },
{
    path: "/forgot-password",
    errorElement: <RouteErrorBoundary />,
    element: (
      <PublicRoute>
        <PageLoader>
          <ForgotPasswordPage />
        </PageLoader>
      </PublicRoute>
    ),
  },
{
    path: "/reset-password/:uid/:token",
    errorElement: <RouteErrorBoundary />,
    element: (
      <PublicRoute>
        <PageLoader>
          <ResetPasswordPage />
        </PageLoader>
      </PublicRoute>
    ),
  },
{
    path: "/recover-account",
    errorElement: <RouteErrorBoundary />,
    element: <PageLoader><AccountRecoveryPage /></PageLoader>,
  },
{
    path: "/invite/:token",
    errorElement: <RouteErrorBoundary />,
    element: (
      <PageLoader>
        <InviteAcceptPage />
      </PageLoader>
    ),
  }
];

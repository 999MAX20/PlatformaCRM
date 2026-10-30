import { Suspense, useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router";
import { PermissionGate } from "../components/auth/PermissionGate";

import { ForbiddenState, LoadingState } from "../components/ui/StateViews";
import { clearSessionExpiredReturnTo, getSessionExpiredReturnTo, isSafeInternalReturnPath } from "../api/client";
import { useAuth } from "../features/auth/AuthProvider";

import { getAuthReturnPathFromState } from "../features/auth/authReturnPath";

import { useActiveBusiness } from "../hooks/useBusiness";
import { useI18n } from "../lib/i18n";
import { permissionForbiddenMessage } from "../lib/permissions";
import { getUserStartPath } from "../lib/startPage";
export function MerchantRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, isMerchantUser, isPlatformUser } =
    useAuth();
  const location = useLocation();
  if (isLoading) return <LoadingState scope="page" />;
  if (!isAuthenticated) return <Navigate to="/login" replace state={{ from: location }} />;
  if (!isMerchantUser && isPlatformUser)
    return <Navigate to="/platform" replace />;
  return isMerchantUser ? children : <Navigate to="/login" replace />;
}
export function PlatformRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, isPlatformUser } = useAuth();
  const location = useLocation();
  if (isLoading) return <LoadingState scope="page" />;
  if (!isAuthenticated) return <Navigate to="/login" replace state={{ from: location }} />;
  return isPlatformUser ? children : <Navigate to="/app/dashboard" replace />;
}
export function PublicRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, isPlatformUser } = useAuth();
  const location = useLocation();
  const [storedReturnTo] = useState(() => getSessionExpiredReturnTo());

  useEffect(() => {
    if (isAuthenticated) clearSessionExpiredReturnTo();
  }, [isAuthenticated]);

  if (isLoading) return <LoadingState scope="page" />;
  if (!isAuthenticated) return children;

  const stateReturnTo = getAuthReturnPathFromState(location.state);
  const intendedPath = stateReturnTo || storedReturnTo;
  const fallback = isPlatformUser ? "/platform" : "/app";

  if (!intendedPath) return <Navigate to={fallback} replace />;
  if (intendedPath.startsWith("/invite/")) return <Navigate to={intendedPath} replace />;
  if (!isSafeInternalReturnPath(intendedPath)) return <Navigate to={fallback} replace />;
  if (isPlatformUser && !intendedPath.startsWith("/platform")) return <Navigate to={fallback} replace />;
  if (!isPlatformUser && !intendedPath.startsWith("/app")) return <Navigate to={fallback} replace />;

  return <Navigate to={intendedPath} replace />;
}
export function PageLoader({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<LoadingState scope="page" />}>
      {children}
    </Suspense>
  );
}
export function PermissionRoute({
  resource,
  action = "view",
  children,
}: {
  resource?: string;
  action?: string;
  children: React.ReactNode;
}) {
  const { user } = useAuth();
  const { t } = useI18n();
  const { business, isLoading } = useActiveBusiness();
  if (!resource) return children;
  if (isLoading) return <LoadingState scope="page" />;
  if (!user || !business?.id)
    return (
      <ForbiddenState
        message={permissionForbiddenMessage(resource, action, t)}
      />
    );
  return (
    <PermissionGate resource={resource} action={action} mode="forbidden">
      {children}
    </PermissionGate>
  );
}
export function UserStartRedirect() {
  const { user } = useAuth();
  const { business, isLoading } = useActiveBusiness();
  if (isLoading) return <LoadingState scope="page" />;
  return <Navigate to={getUserStartPath(user, business?.id)} replace />;
}
export function LegacyDashboardRedirect() {
  const location = useLocation();
  const legacySuffix = location.pathname.replace(/^\/dashboard(?=\/|$)/, "");
  const targetPath = !legacySuffix || legacySuffix === "/"
    ? "/app/dashboard"
    : `/app${legacySuffix}`;
  return (
    <Navigate to={`${targetPath}${location.search}${location.hash}`} replace />
  );
}
export function BusinessRouteRedirect({ section }: { section: "services" | "resources" | "working-hours" }) {
  const location = useLocation();
  return (
    <Navigate
      to={`/app/business/${section}${location.search}${location.hash}`}
      replace
    />
  );
}

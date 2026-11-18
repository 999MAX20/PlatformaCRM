import { useQuery } from "@tanstack/react-query";
import { analyticsApi } from "../../api/analytics";
import { workQueuesQuery } from "./dashboardQueries";
import { ErrorState, PageSkeleton } from "../../components/ui/StateViews";
import { usePageLoading } from "../../components/ui/PageLoadingBoundary";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useI18n } from "../../lib/i18n";
import { hasPermission } from "../../lib/permissions";
import { useAuth } from "../auth/AuthProvider";
import { OperationalDashboard } from "./OperationalDashboard";
import { OwnerDashboard } from "./OwnerDashboard";

export function DashboardPage() {
  const { business, isLoading: businessLoading } = useActiveBusiness();
  const { t } = useI18n();
  const { user } = useAuth();
  const membership = user?.memberships?.find((item) => Number(item.business) === Number(business?.id));
  const isOwnerView = ["owner", "admin", "business_owner"].includes(membership?.role || user?.role || "specialist");
  const permitted = (resource: string) => hasPermission(user, business?.id, resource, "view");
  const canViewAnalytics = permitted("analytics");
  const workQueues = useQuery(workQueuesQuery(business?.id));
  const metrics = useQuery({
    queryKey: ["owner-dashboard", business?.id],
    queryFn: () => analyticsApi.ownerDashboard(business!.id),
    enabled: Boolean(business && isOwnerView && canViewAnalytics),
    staleTime: 30_000,
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
    refetchOnMount: "always",
  });

  usePageLoading(businessLoading || workQueues.isLoading || metrics.isLoading);
  if (businessLoading) return <PageSkeleton />;
  if (!business) return <ErrorState message={t("dashboard.noBusiness")} />;
  return <div className="space-y-4 pb-8" data-testid="dashboard-workspace-ready">
    <OperationalDashboard data={workQueues.data} error={workQueues.error} loading={workQueues.isLoading}
      retry={() => {
        void workQueues.refetch();
        if (isOwnerView && canViewAnalytics) void metrics.refetch();
      }} refreshing={workQueues.isFetching || metrics.isFetching}
      canCreateAppointment={hasPermission(user, business.id, "appointments", "create")}
      connections={isOwnerView && canViewAnalytics && permitted("integrations") ? {
        health: metrics.error ? undefined : metrics.data?.connector_health,
        error: metrics.error, loading: metrics.isLoading,
      } : undefined}
      financial={isOwnerView ? <OwnerDashboard dashboard={metrics.data} metricsError={metrics.error}
        metricsLoading={metrics.isLoading} retryMetrics={() => void metrics.refetch()} canViewAnalytics={canViewAnalytics} /> : null}
      access={{ leads: false, deals: false, tasks: permitted("tasks"),
        appointments: permitted("appointments"), conversations: permitted("conversations") }} />
  </div>;
}

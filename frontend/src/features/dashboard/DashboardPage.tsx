import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { aiApi } from "../../api/ai";
import { analyticsApi } from "../../api/analytics";
import { workQueuesApi } from "../../api/workQueues";
import { ErrorState, PageSkeleton } from "../../components/ui/StateViews";
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
  const [limit, setLimit] = useState(8);
  const membership = user?.memberships?.find((item) => Number(item.business) === Number(business?.id));
  const isOwnerView = ["owner", "admin", "business_owner"].includes(membership?.role || user?.role || "specialist");
  const permitted = (resource: string) => hasPermission(user, business?.id, resource, "view");
  const canViewAnalytics = permitted("analytics");
  const canViewAiAnalyst = permitted("ai_analyst");
  const workQueues = useQuery({
    queryKey: ["work-queues", business?.id, limit],
    queryFn: () => workQueuesApi.get({ business: business!.id, limit }),
    enabled: Boolean(business),
  });
  const metrics = useQuery({
    queryKey: ["owner-dashboard", business?.id],
    queryFn: () => analyticsApi.ownerDashboard(business!.id),
    enabled: Boolean(business && isOwnerView && canViewAnalytics),
  });
  const ownerBrief = useQuery({
    queryKey: ["ai-owner-daily-brief", business?.id],
    queryFn: () => aiApi.ownerDailyBrief({ business: business!.id, limit: 8 }),
    enabled: Boolean(business && isOwnerView && canViewAiAnalyst),
  });

  if (businessLoading) return <PageSkeleton />;
  if (!business) return <ErrorState message={t("dashboard.noBusiness")} />;
  return <div className="space-y-4 pb-8" data-testid="dashboard-workspace-ready">
    <OperationalDashboard data={workQueues.data} error={workQueues.error} loading={workQueues.isLoading}
      retry={() => void workQueues.refetch()} onMore={() => setLimit((value) => Math.min(50, value + 8))}
      access={{ leads: permitted("leads"), deals: permitted("deals"), tasks: permitted("tasks"),
        appointments: permitted("appointments"), conversations: permitted("conversations") }} />
    {isOwnerView ? <OwnerDashboard dashboard={metrics.data} metricsError={metrics.error}
      metricsLoading={metrics.isLoading} retryMetrics={() => void metrics.refetch()} canViewAnalytics={canViewAnalytics}
      ownerBrief={ownerBrief.data} ownerBriefError={ownerBrief.error} canViewAiAnalyst={canViewAiAnalyst} /> : null}
  </div>;
}

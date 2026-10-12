import { useEffect } from "react";
import { useLocation, useNavigate, useParams } from "react-router";
import { usePageHeader } from "../../components/layout/PageHeaderContext";
import { ErrorState, ForbiddenState, LoadingState } from "../../components/ui/StateViews";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useI18n } from "../../lib/i18n";
import { TaskInspector } from "./components/TaskInspector";

export function TaskWorkspacePage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { business, isLoading, error } = useActiveBusiness();
  const { t } = useI18n();
  const { setPageHeader } = usePageHeader();
  useEffect(() => { setPageHeader({ title: t("tasks.title") }); return () => setPageHeader(null); }, [setPageHeader, t]);
  if (!business) return isLoading ? <LoadingState /> : error ? <ErrorState error={error} /> : <ForbiddenState />;
  if (!id || !/^\d+$/.test(id)) return <ErrorState message={t("actions.errorUnavailable")} />;
  const requestedReturn = location.state?.returnTo;
  const returnTo = typeof requestedReturn === "string" && /^\/app\/tasks(?:\?|$)/.test(requestedReturn) ? requestedReturn : "/app/tasks";
  return <div className="p-4 sm:p-6"><TaskInspector key={`${business.id}:${id}`} id={Number(id)} business={business.id} zone={business.timezone || "UTC"} expanded onClose={() => navigate(returnTo)} /></div>;
}

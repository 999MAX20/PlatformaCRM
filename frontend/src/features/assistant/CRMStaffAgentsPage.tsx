import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router";
import { aiApi } from "../../api/ai";
import { Button } from "../../components/ui/Button";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { Tabs } from "../../components/ui/Tabs";
import { usePageHeader } from "../../components/layout/PageHeaderContext";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useI18n } from "../../lib/i18n";
import { hasPermission } from "../../lib/permissions";
import { useAuth } from "../auth/AuthProvider";
import { CRMAgentRuntime } from "./components/CRMAgentRuntime";

export function CRMStaffAgentsPage() {
  const { t } = useI18n();
  const { user } = useAuth();
  const { business, isLoading } = useActiveBusiness();
  const { setPageHeader } = usePageHeader();
  const params = useParams();
  const navigate = useNavigate();
  const canWork = hasPermission(user, business?.id, "ai_assistant", "view");
  const canAnalyze = hasPermission(user, business?.id, "ai_analyst", "view");
  const agents = useQuery({ queryKey: ["ai-runtime-agents", business?.id], queryFn: () => aiApi.runtimeAgents(business!.id), enabled: Boolean(business && (canWork || canAnalyze)) });
  const selected = agents.data?.find(agent => String(agent.id) === params.id) || agents.data?.[0];
  const section = params.section === "analytics" && canAnalyze ? "analytics" : canWork ? "work" : "analytics";
  useEffect(() => { setPageHeader({ title: t("nav.aiAgents") }); return () => setPageHeader(null); }, [setPageHeader, t]);
  useEffect(() => { if (selected && (params.id !== String(selected.id) || params.section !== section)) navigate(`/app/ai-agents/${selected.id}/${section}`, { replace: true }); }, [selected, params.id, params.section, section, navigate]);
  if (isLoading || agents.isLoading) return <LoadingState scope="page" />;
  if (!business || (!canWork && !canAnalyze)) return <ErrorState message={t("aiScenario.noAccess")} />;
  if (agents.error) return <ErrorState error={agents.error} action={<Button onClick={() => agents.refetch()}>{t("common.retry")}</Button>} />;
  if (!selected) return <p className="p-6 text-sm text-platforma-subtle">{t("aiScenario.noAgent")}</p>;
  return <div className="mx-auto w-full max-w-[960px] space-y-5 px-3 py-5 sm:px-6"><h2 className="text-lg font-semibold">{selected.name}</h2>
    <Tabs ariaLabel={t("aiAgents.editorTabsAria")} value={section} onChange={value => navigate(`/app/ai-agents/${selected.id}/${value}`)} options={[...(canWork ? [{ value: "work", label: t("aiScenario.work") }] : []), ...(canAnalyze ? [{ value: "analytics", label: t("aiScenario.analytics") }] : [])]} />
    <CRMAgentRuntime key={`${selected.id}-${section}`} bot={selected} section={section} />
  </div>;
}

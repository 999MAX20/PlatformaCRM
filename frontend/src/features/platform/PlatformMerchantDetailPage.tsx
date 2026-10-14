import { PlatformLoadError } from "./PlatformData";
import { PageHeader } from "../../components/ui/PageHeader";
import { TaskDraftGuard } from "../tasks/components/TaskDraftGuard";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, MessageSquarePlus, RefreshCw } from "lucide-react";
import { useState } from "react";
import { Link, useParams, useLocation } from "react-router";

import { platformApi } from "../../api/platform";
import { getApiErrorMessage } from "../../api/client";
import { issueMfaStepUp } from "../../api/auth";
import { Button } from "../../components/ui/Button";
import { Card, CardBody, CardHeader } from "../../components/ui/Card";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { Textarea } from "../../components/ui/Textarea";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { PlatformMetric, PlatformRecordedSignals, PlatformServiceBadge, platformDate } from "./PlatformData";
import { useI18n } from "../../lib/i18n";

export function PlatformMerchantDetailPage() {
  const { id } = useParams();
  return <PlatformMerchantContent key={id} id={id || ""} />;
}

function PlatformMerchantContent({ id }: { id: string }) {
  const { t, language } = useI18n();
  const location = useLocation();
  const returnTo = typeof location.state?.returnTo === "string" && location.state.returnTo.startsWith("/platform/merchants?") ? location.state.returnTo : "/platform/merchants";
  const [historyPage, setHistoryPage] = useState(1);
  const history = useQuery({ queryKey: ["platform-support-history", id, historyPage], queryFn: () => platformApi.supportActions(id, historyPage), enabled: Boolean(id) });
  const queryClient = useQueryClient();
  const [note, setNote] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [actionType, setActionType] = useState("support_note");
  const locale = language === "kk" ? "kk-KZ" : language === "en" ? "en-US" : "ru-RU";
  const actionOptions = [
    { value: "support_note", label: t("platform.merchantDetail.actionSupportNote") },
    { value: "merchant_call", label: t("platform.merchantDetail.actionMerchantCall") },
    { value: "setup_help", label: t("platform.merchantDetail.actionSetupHelp") },
    { value: "risk_review", label: t("platform.merchantDetail.actionRiskReview") },
  ];
  const merchant = useQuery({
    queryKey: ["platform-merchant", id],
    queryFn: () => platformApi.merchant(id || ""),
    enabled: Boolean(id),
  });
  const supportMutation = useMutation({
    mutationFn: async () => {
      const { step_up_token: stepUpToken } = await issueMfaStepUp(mfaCode);
      return platformApi.createSupportAction(id || "", { action_type: actionType, note }, stepUpToken);
    },
    onSuccess: () => {
      setHistoryPage(1);
      queryClient.invalidateQueries({ queryKey: ["platform-support-history", id] });
      setNote("");
      setMfaCode("");
      queryClient.invalidateQueries({ queryKey: ["platform-merchant", id] });
      queryClient.invalidateQueries({ queryKey: ["platform-merchants"] });
      queryClient.invalidateQueries({ queryKey: ["platform-overview"] });
    },
  });

  if (merchant.isLoading) return <LoadingState scope="page" />;
  if (merchant.isError || !merchant.data) return <PlatformLoadError error={merchant.error} message={t("platform.merchantDetail.error")} onRetry={() => merchant.refetch()} />;

  const data = merchant.data;
  const operations = data.operations;
  return <div className="space-y-5" data-testid="platform-clinic-detail">
    <TaskDraftGuard dirty={Boolean(note.trim())} pending={supportMutation.isPending} />
    <Link to={returnTo} className="platforma-focus-ring inline-flex items-center gap-2 text-sm font-medium text-brand-700"><ArrowLeft size={16} aria-hidden="true" />{t("platform.nav.merchants")}</Link>
    <PageHeader title={data.name} actions={<span className="rounded-control bg-surface-muted px-3 py-2 text-sm">{t(`platform.workspace.status.${data.status}`)}</span>} />
    <Card><CardBody className="grid gap-4 p-4 sm:grid-cols-2 lg:grid-cols-4">
      <div className="min-w-0"><p className="text-xs text-platforma-faint">{t("platform.merchantDetail.owner")}</p><p className="mt-1 font-medium">{data.owner.full_name || t("platform.common.noName")}</p><p className="mt-1 break-all text-sm text-platforma-subtle">{data.owner.email}</p></div>
      <div><p className="text-xs text-platforma-faint">{t("platform.merchants.created")}</p><p className="mt-1 text-sm">{platformDate(data.created_at, language)}</p></div>
      <div><p className="text-xs text-platforma-faint">{t("platform.workspace.lastActivity")}</p><p className="mt-1 text-sm">{platformDate(data.latest_activity_at, language)}</p></div>
      <div><p className="text-xs text-platforma-faint">{t("platform.workspace.snapshot")}</p><p className="mt-1 text-sm">{platformDate(data.generated_at, language)}</p><p className="mt-1 text-xs text-platforma-faint">#{data.id}</p></div>
    </CardBody></Card>
    <div className="grid gap-5 lg:grid-cols-2">
      <Card>
        <CardHeader><div className="flex flex-wrap items-center justify-between gap-2"><h2 className="font-semibold">{t("platform.workspace.serviceTitle")}</h2><PlatformServiceBadge service={data.service_status} /></div></CardHeader>
        <CardBody className="space-y-3 p-4">
          {!data.service_status?.components.length && <p role="status" className="text-sm text-platforma-subtle">{t("serviceStatus.unknown.text")}</p>}
          {data.service_status?.components.map(component => <div key={component.component} className="flex flex-wrap items-start justify-between gap-2 border-b border-platforma-border pb-3 last:border-0 last:pb-0">
            <div><p className="text-sm font-medium">{t(`serviceStatus.component.${component.component}`)}</p><p className="mt-1 text-xs text-platforma-faint">{t("platform.workspace.observedAt", { date: platformDate(component.observed_at, language) })}</p></div>
            <span className={component.state === "degraded" ? "text-sm text-platforma-warning" : "text-sm text-platforma-subtle"}>{t(`platform.workspace.service.${component.state}`)}</span>
          </div>)}
        </CardBody>
      </Card>
      <Card>
        <CardHeader><h2 className="font-semibold">{t("platform.overview.errorsTitle")}</h2></CardHeader>
        <CardBody className="space-y-4 p-4"><PlatformRecordedSignals operations={operations} /><Link to="/platform/operations" className="platforma-focus-ring inline-block text-sm font-medium text-brand-700">{t("platform.nav.operations")}</Link></CardBody>
      </Card>
    </div>
    <div className="grid gap-5 lg:grid-cols-2">
      <Card>
        <CardHeader><h2 className="font-semibold">{t("platform.workspace.configuration")}</h2></CardHeader>
        <CardBody className="p-2"><dl className="grid grid-cols-2">
          <PlatformMetric label={t("platform.workspace.connectedSourcesTitle")} value={operations?.connected_connectors} />
          <PlatformMetric label={t("platform.workspace.pendingSourcesTitle")} value={operations?.pending_connectors} />
          <PlatformMetric label={t("platform.workspace.activeForms")} value={operations?.lead_forms} />
          <div className="min-w-0 p-3"><dt className="text-sm text-platforma-subtle">{t("platform.merchantDetail.landing")}</dt><dd className="mt-1 break-all text-sm">{data.landing_domain || data.landing_id || t("platform.merchantDetail.notConnected")}</dd></div>
        </dl></CardBody>
      </Card>
      <Card>
        <CardHeader><h2 className="font-semibold">{t("platform.merchantDetail.crmOperations")}</h2></CardHeader>
        <CardBody className="p-2"><dl className="grid grid-cols-2 sm:grid-cols-3">
          <PlatformMetric label={t("platform.workspace.leads")} value={operations?.lead_count} />
          <PlatformMetric label={t("platform.workspace.clients")} value={operations?.clients_count} />
          <PlatformMetric label={t("platform.workspace.openTasks")} value={operations?.open_tasks} />
          <PlatformMetric label={t("platform.workspace.unread")} value={operations?.unread_conversations} />
          <PlatformMetric label={t("platform.overview.handoffConversations")} value={operations?.handoff_conversations} />
          <PlatformMetric label={t("platform.workspace.salesEvents")} value={operations?.sales_events} />
        </dl></CardBody>
      </Card>
    </div>
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <MessageSquarePlus className="text-brand-600" size={21} />
              <p className="text-lg font-semibold text-platforma-text">{t("platform.merchantDetail.logSupportAction")}</p>
            </div>
          </CardHeader>
          <CardBody>
            {data.can_log_support_action ? (
              <div data-testid="support-action-form">
                <Select label={t("platform.support.actionType")} value={actionType} onChange={(event) => setActionType(event.target.value)} options={actionOptions} disabled={supportMutation.isPending} />
                <Textarea className="mt-3" label={t("platform.merchantDetail.notePlaceholder")} value={note} onChange={(event) => setNote(event.target.value)} maxLength={4000} disabled={supportMutation.isPending} placeholder={t("platform.merchantDetail.noteTextarea")} />
                <Input
                  className="mt-3"
                  label={t("mfa.codeLabel")}
                  value={mfaCode}
                  onChange={(event) => setMfaCode(event.target.value)}
                  placeholder={t("mfa.codePlaceholder")}
                  autoComplete="one-time-code"
                  disabled={supportMutation.isPending}
                />
                {supportMutation.isError ? <ErrorState error={supportMutation.error} message={getApiErrorMessage(supportMutation.error)} /> : null}
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button onClick={() => supportMutation.mutate()} isLoading={supportMutation.isPending} disabled={!note.trim() || !mfaCode.trim()}>
                    <MessageSquarePlus size={16} /> {t("platform.merchantDetail.saveAction")}
                  </Button>
                </div>
              </div>
            ) : <p className="mb-3 rounded-control bg-surface-muted p-3 text-sm text-platforma-subtle">{t("platform.support.readOnly")}</p>}
            {supportMutation.isSuccess && <p role="status" className="my-3 text-sm text-platforma-success">{t("common.saved")}</p>}
            <Button variant="secondary" onClick={() => { merchant.refetch(); history.refetch(); }} isLoading={merchant.isFetching}>
              <RefreshCw size={16} /> {t("platform.merchantDetail.refresh")}
            </Button>
            <div className="mt-5 space-y-2" data-testid="support-action-history">
              {history.isPending ? <LoadingState /> : history.isError ? <ErrorState error={history.error} action={<Button variant="secondary" onClick={() => history.refetch()}>{t("platform.merchantDetail.refresh")}</Button>} /> : null}
              {(history.data?.results || []).map((action) => (
                <div key={action.id} className="rounded-control border border-platforma-border bg-surface-muted px-3 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-semibold text-platforma-text">{action.action_type}</p>
                    <span className="rounded-full bg-surface-card px-2 py-1 text-[11px] font-bold text-platforma-faint">{action.status}</span>
                  </div>
                  <p className="mt-1 text-sm leading-6 text-platforma-subtle">{action.note}</p>
                  <p className="mt-2 text-xs font-semibold text-platforma-faint">{action.actor_email || t("platform.title")} · {new Date(action.created_at).toLocaleString(locale)}</p>
                </div>
              ))}
              {history.isSuccess && !history.data.results.length ? (
                <p className="rounded-control bg-surface-muted p-4 text-sm text-platforma-faint">
                  {t("platform.merchantDetail.noRecentActions")}
                </p>
              ) : null}
            </div>
            {history.isSuccess && <div className="mt-4 flex flex-wrap items-center justify-between gap-2 text-sm"><span>{t("pagination.total", { total: history.data.count })}</span><div className="flex gap-2"><Button variant="secondary" disabled={!history.data.previous} onClick={() => setHistoryPage(value => value - 1)}>{t("pagination.previous")}</Button><Button variant="secondary" disabled={!history.data.next} onClick={() => setHistoryPage(value => value + 1)}>{t("pagination.next")}</Button></div></div>}
          </CardBody>
        </Card>
    <p className="text-xs text-platforma-faint">{t("platform.workspace.activityScope")} {t("platform.workspace.unknownLegend")}</p>
  </div>;
}

import { PageHeader } from "../../components/ui/PageHeader";
import { TaskDraftGuard } from "../tasks/components/TaskDraftGuard";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CheckCircle2, Headphones, MessageSquarePlus, RefreshCw, ShieldAlert, Store } from "lucide-react";
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
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/StateViews";
import { cn } from "../../lib/cn";
import { useI18n } from "../../lib/i18n";

function statusClass(status?: string | null) {
  if (status === "healthy" || status === "active") return "border-platforma-success/20 bg-[var(--platforma-success-soft)] text-platforma-success";
  if (status === "setup" || status === "trial") return "border-discovery-100 bg-discovery-50 text-discovery-700";
  if (status === "attention" || status === "medium") return "border-platforma-warning/20 bg-[var(--platforma-warning-soft)] text-platforma-warning";
  if (status === "risk" || status === "high" || status === "blocked") return "border-platforma-danger/20 bg-[var(--platforma-danger-soft)] text-platforma-danger";
  return "border-platforma-border bg-surface-muted text-platforma-subtle";
}

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
  if (merchant.isError || !merchant.data) return <ErrorState error={merchant.error} message={t("platform.merchantDetail.error")} action={<Button variant="secondary" onClick={() => merchant.refetch()}>{t("platform.merchantDetail.refresh")}</Button>} />;

  const data = merchant.data;
  const workflow = data.support_workflow;
  const operations = data.operations;
  const health = data.health;

  return (
    <div className="space-y-5">
      <TaskDraftGuard dirty={Boolean(note.trim())} pending={supportMutation.isPending} />
      <Link to={returnTo} className="platforma-focus-ring inline-flex items-center gap-2 text-sm font-medium text-brand-700"><ArrowLeft size={16} aria-hidden="true" />{t("platform.nav.merchants")}</Link>
      <PageHeader title={data.name} actions={<span className="rounded-control bg-surface-muted px-3 py-2 text-sm">{data.status}</span>} />

      <div className="grid gap-4 lg:grid-cols-[1fr_0.9fr]">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <Store className="text-brand-600" size={21} />
              <p className="text-lg font-semibold text-platforma-text">{t("platform.merchantDetail.snapshot")}</p>
            </div>
          </CardHeader>
          <CardBody className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-card border border-platforma-border bg-surface-muted/70 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-platforma-faint">{t("platform.merchantDetail.owner")}</p>
              <p className="mt-2 font-bold text-platforma-text">{data.owner.full_name || t("platform.common.noName")}</p>
              <p className="mt-1 text-sm text-platforma-faint">{data.owner.email}</p>
            </div>
            <div className="rounded-card border border-platforma-border bg-surface-muted/70 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-platforma-faint">{t("platform.merchantDetail.landing")}</p>
              <p className="mt-2 font-bold text-platforma-text">{data.landing_domain || t("platform.merchantDetail.notConnected")}</p>
              <p className="mt-1 text-sm text-platforma-faint">{data.landing_id || t("platform.merchantDetail.noLandingId")}</p>
            </div>
            <div className="rounded-card border border-platforma-border bg-surface-muted/70 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-platforma-faint">{t("platform.merchantDetail.crmOperations")}</p>
              <p className="mt-2 text-sm font-semibold leading-6 text-platforma-subtle">
                {t("platform.merchantDetail.leadsLine", { leads: operations?.lead_count ?? 0, new: operations?.new_leads ?? 0 })}<br />
                {t("platform.merchantDetail.clientsLine", { clients: operations?.clients_count ?? 0, tasks: operations?.open_tasks ?? 0 })}<br />
                {t("platform.merchantDetail.inboxLine", { unread: operations?.unread_conversations ?? 0, handoff: operations?.handoff_conversations ?? 0 })}
              </p>
            </div>
            <div className="rounded-card border border-platforma-border bg-surface-muted/70 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-platforma-faint">{t("platform.merchantDetail.dataSources")}</p>
              <p className="mt-2 text-sm font-semibold leading-6 text-platforma-subtle">
                {t("platform.merchantDetail.connectorsLine", { ok: operations?.connected_connectors ?? 0, pending: operations?.pending_connectors ?? 0, failed: operations?.failed_connectors ?? 0 })}<br />
                {t("platform.merchantDetail.formsLine", { forms: operations?.lead_forms ?? 0, errors: operations?.form_errors ?? 0 })}<br />
                {t("platform.merchantDetail.salesEventsLine", { events: operations?.sales_events ?? 0 })}
              </p>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <ShieldAlert className={health?.status === "risk" ? "text-platforma-danger" : "text-platforma-warning"} size={21} />
              <p className="text-lg font-semibold text-platforma-text">{t("platform.merchantDetail.pilotHealth")}</p>
            </div>
          </CardHeader>
          <CardBody>
            <p className="text-sm leading-6 text-platforma-subtle">{health?.next_action || t("platform.merchantDetail.monitorPilot")}</p>
            <div className="mt-4 space-y-2">
              {(health?.blockers || []).map((blocker) => (
                <div key={blocker} className="rounded-control border border-platforma-warning/20 bg-[var(--platforma-warning-soft)] px-3 py-2 text-sm font-semibold text-platforma-warning">
                  {blocker}
                </div>
              ))}
              {!health?.blockers?.length ? (
                <div className="rounded-control border border-platforma-success/20 bg-[var(--platforma-success-soft)] px-3 py-2 text-sm font-semibold text-platforma-success">
                  {t("platform.merchantDetail.noBlockers")}
                </div>
              ) : null}
            </div>
          </CardBody>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <Headphones className="text-brand-600" size={21} />
              <p className="text-lg font-semibold text-platforma-text">{t("platform.merchantDetail.supportWorkflow")}</p>
            </div>
          </CardHeader>
          <CardBody>
            <span className={cn("inline-flex rounded-full border px-3 py-1 text-xs font-semibold uppercase", statusClass(workflow?.priority))}>
              {t("platform.merchantDetail.priority", { priority: workflow?.priority || "low" })}
            </span>
            <p className="mt-4 text-sm leading-6 text-platforma-subtle">{workflow?.summary || t("platform.merchantDetail.emptyWorkflow")}</p>
            <div className="mt-4 space-y-2">
              {(workflow?.next_steps || []).map((step) => (
                <div key={step.key} className="flex items-center justify-between rounded-control border border-platforma-border bg-surface-muted px-3 py-3 text-sm font-bold text-platforma-text transition hover:bg-surface-card hover:shadow-soft">
                  {step.label}
                  <CheckCircle2 size={16} className="text-brand-600" aria-hidden="true" />
                </div>
              ))}
              {!workflow?.next_steps?.length ? <EmptyState title={t("platform.merchantDetail.noNextSteps")} description={t("platform.merchantDetail.noNextStepsText")} /> : null}
            </div>
          </CardBody>
        </Card>

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
      </div>
    </div>
  );
}

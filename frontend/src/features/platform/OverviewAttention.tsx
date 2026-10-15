import { Link } from "react-router";
import { Card, CardBody, CardHeader } from "../../components/ui/Card";
import { EmptyState } from "../../components/ui/StateViews";
import { StatusNotice } from "../../components/ui/StatusNotice";
import { useI18n } from "../../lib/i18n";
import type { OverviewAttention as Attention } from "../../types/platformOverview";
import { incidentPath } from "../support/SupportIncidents";
import { SupportStatusBadge } from "../support/SupportUI";
import { PlatformMetric, platformDate, valueOrUnknown } from "./PlatformData";

const linkClass = "platforma-focus-ring rounded-control text-sm font-medium text-brand-700 hover:underline";
const overviewContext = { returnTo: "/platform" };

export function OverviewAttention({ data }: { data: Attention }) {
  const { t, language } = useI18n();
  return <div className="space-y-4" data-testid="overview-attention">
    {!!data.unavailable_sources.length && <StatusNotice compact tone="warning" title={t("platform.workspace.partial")} />}
    <Card variant="outlined"><CardBody className="p-1"><dl className="grid grid-cols-2 lg:grid-cols-5">
      <PlatformMetric label={t("overviewWorkspace.degradedClinics")} value={data.clinics?.degraded} href="/platform/merchants?service=degraded" />
      <PlatformMetric label={t("overviewWorkspace.unknownClinics")} value={data.clinics?.unknown} href="/platform/merchants?service=unknown" />
      <PlatformMetric label={t("overviewWorkspace.activeCases")} value={data.support?.count} href="/platform/support?status=active" />
      <PlatformMetric label={t("overviewWorkspace.unassignedCases")} value={data.support?.unassigned} href="/platform/support?status=active&assignee=unassigned" />
      <PlatformMetric label={t("supportCases.status.waiting_clinic")} value={data.support?.waiting_clinic} href="/platform/support?status=waiting_clinic" />
    </dl></CardBody></Card>
    <div className="grid items-start gap-4 xl:grid-cols-2">
      <Card variant="outlined" data-testid="overview-clinics">
        <CardHeader className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-semibold">{t("overviewWorkspace.clinicQueue")}</h2>
          <Link className={linkClass} to="/platform/merchants?service=attention">{t("overviewWorkspace.allClinics", { count: valueOrUnknown(data.clinics?.count) })}</Link>
        </CardHeader>
        {!data.clinics ? <EmptyState title={t("platform.workspace.unknown")} /> : !data.clinics.count ? <EmptyState title={t("overviewWorkspace.noClinicAttention")} /> : <>
          {!data.clinics.links_available && <div className="p-3"><StatusNotice compact tone="warning" title={t("platform.workspace.partial")} /></div>}
          <ul className="divide-y divide-platforma-border">{data.clinics.results.map(clinic => <li key={clinic.id} className="grid gap-2 px-4 py-3 sm:grid-cols-[minmax(0,1fr)_auto]" data-testid="overview-clinic-row">
            <div className="min-w-0">
              <Link state={overviewContext} to={`/platform/merchants/${clinic.id}`} className={`${linkClass} break-words font-semibold`}>{clinic.name} · #{clinic.id}</Link>
              <details className="mt-1 text-xs"><summary className="platforma-focus-ring cursor-pointer rounded-control py-1 text-platforma-subtle">{clinic.components.map(item => t(`serviceStatus.component.${item.component}`)).join(" · ")}</summary>
                <ul className="mt-2 space-y-2">{clinic.components.map(item => <li key={item.component} className="space-y-1 rounded-control bg-surface-muted p-3">
                  <p className="font-medium">{t(`serviceStatus.component.${item.component}`)} · {t(`platform.workspace.service.${item.state}`)}</p>
                  <p className="text-platforma-subtle">{t("supportIncidents.observed")}: {platformDate(item.observed_at, language)}</p>
                  {item.started_at && <p className="text-platforma-subtle">{t("supportIncidents.started")}: {platformDate(item.started_at, language)}</p>}
                  {item.episode > 0 && <Link state={overviewContext} className={`${linkClass} inline-flex min-h-10 items-center`} to={incidentPath(clinic.id, item.component, item.episode)}>{t("supportIncidents.open")} · {t("operationsWorkspace.linkedCases", { count: valueOrUnknown(item.linked_cases) })}</Link>}
                </li>)}</ul>
              </details>
            </div>
            <div className="flex items-center justify-between gap-3 sm:flex-col sm:items-end sm:justify-start">
              <span className={`text-xs ${clinic.status === "degraded" ? "text-platforma-warning" : "text-platforma-subtle"}`}>{t(`platform.workspace.service.${clinic.status}`)}</span>
              <Link className={linkClass} to={`/platform/operations?business=${clinic.id}`}>{t("platform.nav.operations")}</Link>
            </div>
          </li>)}</ul>
          <p className="border-t border-platforma-border px-4 py-3 text-xs text-platforma-subtle">{t("overviewWorkspace.clinicOrder", { shown: data.clinics.results.length, total: data.clinics.count })}</p>
        </>}
      </Card>
      <Card variant="outlined" data-testid="overview-support">
        <CardHeader className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-semibold">{t("overviewWorkspace.supportQueue")}</h2>
          <Link className={linkClass} to="/platform/support?status=active">{t("overviewWorkspace.allCases", { count: valueOrUnknown(data.support?.count) })}</Link>
        </CardHeader>
        {!data.support ? <EmptyState title={t("platform.workspace.unknown")} /> : !data.support.count ? <EmptyState title={t("overviewWorkspace.noOpenCases")} /> : <>
          <ul className="divide-y divide-platforma-border">{data.support.results.map(item => <li key={item.id} className="grid gap-2 px-4 py-3 sm:grid-cols-[minmax(0,1fr)_auto]" data-testid="overview-case-row">
            <div className="min-w-0 space-y-1">
              <Link state={overviewContext} className={`${linkClass} break-words font-semibold`} to={`/platform/support/${item.id}`}>#{item.id} · {item.subject}</Link>
              <p className="break-words text-xs text-platforma-subtle">{item.business_name}</p>
              <p className="text-xs text-platforma-faint">{t("supportCases.updated")}: {platformDate(item.updated_at, language)}</p>
            </div>
            <div className="flex flex-wrap items-center gap-2 sm:max-w-48 sm:flex-col sm:items-end">
              <SupportStatusBadge status={item.status} />
              <span className="break-words text-xs text-platforma-subtle">{t("supportCases.assignee")}: {item.assignee?.name || t("supportCases.filter.unassigned")}</span>
              {item.assignee?.available === false && <p className="text-xs text-platforma-warning">{t("supportCases.assigneeUnavailable")}</p>}
            </div>
          </li>)}</ul>
          <p className="border-t border-platforma-border px-4 py-3 text-xs text-platforma-subtle">{t("overviewWorkspace.supportOrder", { shown: data.support.results.length, total: data.support.count })}</p>
        </>}
      </Card>
    </div>
  </div>;
}

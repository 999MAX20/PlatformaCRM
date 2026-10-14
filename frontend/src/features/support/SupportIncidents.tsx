import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";
import { supportApi } from "../../api/support";
import { Card } from "../../components/ui/Card";
import { LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import type { SupportIncident } from "../../types/support";
import { SupportPager } from "./SupportThread";
import { SupportError, supportDate } from "./SupportUI";

export const incidentPath = (business: number | string, component: string, episode: number) => `/platform/merchants/${business}/incidents/${encodeURIComponent(component)}/${episode}`;

export function IncidentSummary({ incident }: { incident: SupportIncident }) {
  const { t, language } = useI18n();
  const current = incident.current;
  return <dl className="grid gap-3 text-sm sm:grid-cols-2" data-testid="support-incident-summary">
    <div><dt className="text-xs text-platforma-subtle">{t("supportIncidents.source")}</dt><dd>{t(`serviceStatus.component.${incident.component}`)} · #{incident.episode}</dd></div>
    <div><dt className="text-xs text-platforma-subtle">{t("supportIncidents.started")}</dt><dd>{supportDate(incident.started_at, language, "UTC")} UTC</dd></div>
    <div><dt className="text-xs text-platforma-subtle">{t("supportIncidents.current")}</dt><dd>{t(incident.historical ? "supportIncidents.historical" : `platform.workspace.service.${current?.state || "unknown"}`)}</dd></div>
    {current && <div><dt className="text-xs text-platforma-subtle">{t("supportIncidents.observed")}</dt><dd>{supportDate(current.observed_at, language, "UTC")} UTC · {t("serviceStatus.platform.overdue", { count: current.affected_count })}</dd></div>}
    {current?.recovered_at && <div><dt className="text-xs text-platforma-subtle">{t("supportIncidents.recovered")}</dt><dd>{supportDate(current.recovered_at, language, "UTC")} UTC</dd></div>}
    {incident.snapshot && <div><dt className="text-xs text-platforma-subtle">{t("supportIncidents.snapshot")}</dt><dd>{t(`platform.workspace.service.${incident.snapshot.state}`)} · {supportDate(incident.snapshot.observed_at, language, "UTC")} UTC</dd></div>}
  </dl>;
}

export function SupportIncidents({ caseId }: { caseId: number }) {
  const { t } = useI18n();
  const [page, setPage] = useState(1);
  const links = useQuery({ queryKey: ["support", "platform", "incident-links", caseId, page], queryFn: () => supportApi.caseIncidents(caseId, page), refetchInterval: 30_000 });
  return <Card padding="md" className="space-y-4" data-testid="support-incident-links">
    <h2 className="font-semibold">{t("supportIncidents.title")}</h2>
    {links.isPending ? <LoadingState /> : links.isError ? <SupportError error={links.error} retry={() => links.refetch()} /> : !links.data.count ? <p className="text-sm text-platforma-subtle">{t("supportIncidents.empty")}</p> : <>
      {links.data.results.map(incident => <article key={incident.id} className="space-y-3 rounded-control border border-platforma-border p-3">
        <IncidentSummary incident={incident} />
        <Link className="platforma-focus-ring inline-flex min-h-10 items-center text-sm text-brand-700" to={incidentPath(incident.business, incident.component, incident.episode)}>{t("supportIncidents.open")}</Link>
      </article>)}
      <SupportPager page={page} pageSize={10} total={links.data.count} onChange={setPage} />
    </>}
  </Card>;
}

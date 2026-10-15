import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate, useParams, useLocation } from "react-router";
import { supportApi } from "../../api/support";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { PageHeader } from "../../components/ui/PageHeader";
import { EmptyState, LoadingState } from "../../components/ui/StateViews";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";
import { useI18n } from "../../lib/i18n";
import { SupportCreateDialog } from "./SupportCreateDialog";
import { IncidentSummary } from "./SupportIncidents";
import { SupportPager } from "./SupportThread";
import { SupportError, SupportStatusBadge, retainSupportData } from "./SupportUI";

export function SupportIncidentPage() {
  const params = useParams();
  const { t } = useI18n();
  const business = Number(params.id), episode = Number(params.episode), component = params.component || "";
  if (!Number.isSafeInteger(business) || business < 1 || !Number.isSafeInteger(episode) || episode < 1 || !["automations", "notifications", "exports", "files"].includes(component)) return <EmptyState title={t("supportCases.unavailable")} />;
  return <IncidentContent key={`${business}-${component}-${episode}`} business={business} component={component} episode={episode} />;
}

function IncidentContent({ business, component, episode }: { business: number; component: string; episode: number }) {
  const { t } = useI18n();
  const navigate = useNavigate(), queryClient = useQueryClient();
  const location = useLocation();
  const returnTo = typeof location.state?.returnTo === "string" && /^\/platform\/operations(\?|$)/.test(location.state.returnTo) ? location.state.returnTo : null;
  const [page, setPage] = useState(1), [creating, setCreating] = useState(false);
  const [search, setSearch] = useState(""), [caseId, setCaseId] = useState("");
  const needle = useDebouncedValue(search, 250);
  const reference = { component, episode };
  const result = useQuery({ queryKey: ["support", "platform", "incident", business, component, episode, page], queryFn: () => supportApi.incident(business, reference, page), refetchInterval: 30_000 });
  const candidates = useQuery({ queryKey: ["support", "platform", "incident-candidates", business, needle], queryFn: () => supportApi.list({ platform: true }, { business, search: needle, page_size: 20 }) });
  const link = useMutation({ mutationFn: () => supportApi.linkIncident(Number(caseId), business, reference), onSuccess: () => { setCaseId(""); setPage(1); queryClient.invalidateQueries({ queryKey: ["support", "platform"] }); } });
  if (result.isPending) return <LoadingState scope="page" />;
  if (!result.data || (result.isError && !retainSupportData(result.error))) return <SupportError error={result.error} retry={() => result.refetch()} />;
  const item = result.data;
  return <div className="space-y-4" data-testid="support-incident-page">
    {returnTo && <Link className="platforma-focus-ring inline-flex min-h-10 items-center text-sm text-brand-700" to={returnTo}>{t("platform.nav.operations")}</Link>}
    <Link className="platforma-focus-ring inline-flex min-h-10 items-center text-sm text-brand-700" to={`/platform/merchants/${business}`}>{t("supportIncidents.back")}</Link>
    <PageHeader title={t("supportIncidents.open")} actions={<Button variant="secondary" onClick={() => result.refetch()} isLoading={result.isFetching}>{t("common.refresh")}</Button>} />
    {result.isError && <SupportError error={result.error} retry={() => result.refetch()} />}
    <Card padding="md" className="space-y-4"><p className="font-semibold">{item.incident.business_name} · #{business}</p><IncidentSummary incident={item.incident} /></Card>
    <Card padding="md" className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2"><h2 className="font-semibold">{t("supportIncidents.cases")}</h2><Button id="support-create-button" disabled={item.incident.historical} onClick={() => setCreating(true)}>{t("supportCases.create")}</Button></div>
      {item.results.length ? <ul className="divide-y divide-platforma-border">{item.results.map(row => <li key={row.id} className="flex flex-wrap items-center justify-between gap-2 py-3"><Link className="platforma-focus-ring min-w-0 break-words text-sm font-semibold text-brand-700" to={`/platform/support/${row.id}`}>{row.number} · {row.subject}</Link><SupportStatusBadge status={row.status} /></li>)}</ul> : <p className="text-sm text-platforma-subtle">{t("supportIncidents.noCases")}</p>}
      <SupportPager page={page} pageSize={10} total={item.count} onChange={setPage} />
      {!item.incident.historical && <form className="space-y-3 border-t border-platforma-border pt-4" onSubmit={event => { event.preventDefault(); link.mutate(); }}>
        <Input label={t("supportCases.search")} value={search} onChange={event => { setSearch(event.target.value); setCaseId(""); }} disabled={link.isPending} />
        <Select label={t("supportIncidents.existing")} value={caseId} onChange={event => setCaseId(event.target.value)} disabled={link.isPending || candidates.isFetching} options={[{ value: "", label: t("supportIncidents.choose") }, ...(candidates.data?.results || []).map(row => ({ value: String(row.id), label: `${row.number} · ${row.subject}` }))]} />
        {candidates.isError && <SupportError error={candidates.error} retry={() => candidates.refetch()} />}
        {link.isError && <SupportError error={link.error} retry={() => result.refetch()} />}
        {link.isSuccess && <p role="status" className="text-sm text-brand-700">{t("supportIncidents.linked")}</p>}
        <Button type="submit" disabled={!caseId || candidates.isError} isLoading={link.isPending}>{t("supportIncidents.link")}</Button>
      </form>}
    </Card>
    {creating && <SupportCreateDialog scope={{ platform: true }} initialBusiness={business} incident={reference} onClose={() => setCreating(false)} onCreated={row => navigate(`/platform/support/${row.id}`)} />}
  </div>;
}

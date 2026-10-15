import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { Link, useLocation, useParams } from "react-router";
import { supportApi } from "../../api/support";
import { DraftGuard } from "../../components/actions/DraftGuard";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { PlatformPageHeading } from "../../components/layout/PlatformPageHeading";
import { PageHeader } from "../../components/ui/PageHeader";
import { EmptyState, LoadingState } from "../../components/ui/StateViews";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useI18n } from "../../lib/i18n";
import type { SupportCase, SupportScope } from "../../types/support";
import { SupportActionDialog, type SupportAction } from "./SupportActionDialog";
import { SupportPager, SupportThread } from "./SupportThread";
import { SupportIncidents } from "./SupportIncidents";
import { SupportError, SupportStatusBadge, retainSupportData, supportDate } from "./SupportUI";

export function SupportDetailPage({ platform = false }: { platform?: boolean }) {
  const { id } = useParams();
  const active = useActiveBusiness();
  const { t } = useI18n();
  const business = platform ? undefined : active.business?.id;
  const scope = useMemo<SupportScope>(() => ({ platform, business }), [platform, business]);
  if (!platform && active.isLoading) return <LoadingState scope="page" />;
  if (!platform && active.isError) return <SupportError error={active.error} retry={() => active.refetch()} />;
  if (!Number.isSafeInteger(Number(id)) || Number(id) < 1 || (!platform && !business)) return <EmptyState title={t("supportCases.unavailable")} />;
  return <SupportDetail key={`${platform}-${business}-${id}`} id={Number(id)} scope={scope} />;
}

function SupportDetail({ id, scope }: { id: number; scope: SupportScope }) {
  const { t } = useI18n();
  const location = useLocation();
  const root = scope.platform ? "/platform/support" : "/app/support";
  const returnTo = typeof location.state?.returnTo === "string" && (location.state.returnTo === root || location.state.returnTo.startsWith(root + "?") || (scope.platform && (location.state.returnTo === "/platform" || /^\/platform\/merchants\/\d+\?section=support(?:&|$)/.test(location.state.returnTo)))) ? location.state.returnTo : root;
  const [drafts, setDrafts] = useState<Record<string, { dirty: boolean; pending: boolean }>>({});
  const [action, setAction] = useState<SupportAction | null>(null);
  const onDraft = useCallback((name: string, dirty: boolean, pending: boolean) => setDrafts(current => current[name]?.dirty === dirty && current[name]?.pending === pending ? current : { ...current, [name]: { dirty, pending } }), []);
  const detail = useQuery({
    queryKey: ["support", scope.platform ? "platform" : "clinic", scope.business, "case", id],
    queryFn: () => supportApi.detail(scope, id), refetchInterval: 30_000,
  });
  if (detail.isPending) return <LoadingState scope="page" />;
  if (!detail.data || (detail.isError && !retainSupportData(detail.error))) return <SupportError error={detail.error} retry={() => detail.refetch()} />;
  const item = detail.data;
  return <div className="space-y-4" data-testid="support-case-detail">
    <DraftGuard dirty={Object.values(drafts).some(draft => draft.dirty)} pending={Object.values(drafts).some(draft => draft.pending)} />
    {detail.isError && <SupportError error={detail.error} retry={() => detail.refetch()} />}
    <Link to={returnTo} className="platforma-focus-ring inline-flex min-h-10 items-center gap-2 text-sm font-medium text-brand-700"><ArrowLeft size={16} aria-hidden="true" />{t(returnTo === "/platform" ? "platform.nav.overview" : "supportCases.back")}</Link>
    {scope.platform ? <PlatformPageHeading title={`${t("platform.shell.case")} ${item.number}`} subject={item.subject} actions={<Button variant="secondary" onClick={() => detail.refetch()} isLoading={detail.isFetching}>{t("common.refresh")}</Button>} /> : <PageHeader title={item.subject} actions={<Button variant="secondary" onClick={() => detail.refetch()} isLoading={detail.isFetching}>{t("common.refresh")}</Button>} />}
    <Card padding="md" className="space-y-3">
      <div className="flex flex-wrap items-center gap-3"><span className="font-semibold">{item.number}</span><SupportStatusBadge status={item.status} /><span className="text-sm text-platforma-subtle">{t(`supportCases.source.${item.source}`)}</span></div>
      <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
        <div><dt className="text-xs text-platforma-subtle">{t("supportCases.clinic")}</dt><dd className="mt-1 break-words">{scope.platform ? <Link to={`/platform/merchants/${item.business}`} className="platforma-focus-ring text-brand-700">{item.business_name}</Link> : item.business_name}</dd></div>
        <div><dt className="text-xs text-platforma-subtle">{t("supportCases.author")}</dt><dd className="mt-1 break-words">{item.author.name}</dd></div>
        <div><dt className="text-xs text-platforma-subtle">{t("supportCases.contact")}</dt><dd className="mt-1 break-words">{item.contact.name}</dd></div>
        <div><dt className="text-xs text-platforma-subtle">{t("supportCases.assignee")}</dt><dd className="mt-1 break-words">{item.assignee?.name || t("supportCases.filter.unassigned")}</dd>{item.assignee?.available === false && <p className="mt-1 text-xs text-platforma-warning">{t("supportCases.assigneeUnavailable")}</p>}</div>
      </dl>
      <div className="flex flex-wrap gap-2">
        {item.available_actions.assign && <Button variant="secondary" onClick={() => setAction("assign")}>{t("supportCases.assign")}</Button>}
        {item.available_actions.transitions.map(status => <Button key={status} variant={status === "resolved" ? "primary" : "secondary"} onClick={() => setAction(status)}>{t(`supportCases.action.${status}`)}</Button>)}
        {item.available_actions.reopen && <Button variant="secondary" onClick={() => setAction("reopen")}>{t("supportCases.reopen")}</Button>}
      </div>
      <p className="text-xs text-platforma-subtle">{item.business_timezone}</p>
    </Card>
    <div className={scope.platform ? "grid min-w-0 items-start gap-4 xl:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]" : "min-w-0"}>
      <SupportThread item={item} scope={scope} onDraft={onDraft} />
      {item.available_actions.internal_note && <SupportThread item={item} scope={scope} internal onDraft={onDraft} />}
    </div>
    <SupportHistory item={item} scope={scope} />
    {scope.platform && <SupportIncidents caseId={item.id} />}
    {action && <SupportActionDialog key={action} item={item} scope={scope} action={action} onClose={() => setAction(null)} onDraft={onDraft} />}
  </div>;
}

function SupportHistory({ item, scope }: { item: SupportCase; scope: SupportScope }) {
  const { t, language } = useI18n();
  const [page, setPage] = useState(1);
  const history = useQuery({
    queryKey: ["support", scope.platform ? "platform" : "clinic", scope.business, "events", item.id, page],
    queryFn: () => supportApi.events(scope, item.id, page), refetchInterval: 30_000,
  });
  return <Card padding="md" className="space-y-3" data-testid="support-case-history">
    <h2 className="font-semibold">{t("supportCases.history")}</h2>
    {history.isPending ? <LoadingState /> : history.isError ? <SupportError error={history.error} retry={() => history.refetch()} /> : <ul className="divide-y divide-platforma-border">
      {history.data.results.map(event => <li key={event.id} className="py-3 text-sm">
        <div className="flex flex-wrap justify-between gap-2"><p className="break-words font-medium">{t(`supportCases.event.${event.kind}`)} · {event.actor.name}</p><time className="text-xs text-platforma-subtle" dateTime={event.created_at}>{supportDate(event.created_at, language, item.business_timezone)}</time></div>
        {(event.kind === "transitioned" || event.kind === "reopened") && <p className="mt-1 text-xs text-platforma-subtle">{t(`supportCases.status.${event.old_value}`)} → {t(`supportCases.status.${event.new_value}`)}</p>}
        {event.reason && <p className="mt-2 whitespace-pre-wrap [overflow-wrap:anywhere]">{event.reason}</p>}
      </li>)}
    </ul>}
    {history.data && <SupportPager page={page} total={history.data.count} pageSize={10} onChange={setPage} />}
  </Card>;
}

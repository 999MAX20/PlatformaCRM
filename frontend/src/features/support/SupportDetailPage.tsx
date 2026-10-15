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
import { Tabs } from "../../components/ui/Tabs";
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
  const [threadMode, setThreadMode] = useState("public");
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
    {scope.platform ? <div className="grid min-w-0 items-start gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(280px,340px)]">
      <div className="min-w-0 space-y-3">
        {item.available_actions.internal_note && <Tabs value={threadMode} onChange={setThreadMode} idPrefix="support-thread" ariaLabel={t("supportCases.publicThread")} appearance="underline" options={[
          { value: "public", label: t("supportCases.replyClinic") }, { value: "internal", label: t("supportCases.internalText") },
        ]} />}
        <div hidden={threadMode !== "public" && item.available_actions.internal_note} role={item.available_actions.internal_note ? "tabpanel" : undefined} id="support-thread-panel-public" aria-labelledby={item.available_actions.internal_note ? "support-thread-tab-public" : undefined}>
          <SupportThread item={item} scope={scope} active={threadMode === "public" || !item.available_actions.internal_note} onDraft={onDraft} />
        </div>
        {item.available_actions.internal_note && <div hidden={threadMode !== "internal"} role="tabpanel" id="support-thread-panel-internal" aria-labelledby="support-thread-tab-internal">
          <SupportThread item={item} scope={scope} internal onDraft={onDraft} />
        </div>}
      </div>
      <div className="min-w-0 space-y-4">
        <SupportContext item={item} scope={scope} setAction={setAction} />
        <SupportHistory item={item} scope={scope} />
        <SupportIncidents caseId={item.id} />
      </div>
    </div> : <>
      <SupportContext item={item} scope={scope} setAction={setAction} />
      <SupportThread item={item} scope={scope} onDraft={onDraft} />
      <SupportHistory item={item} scope={scope} />
    </>}
    {action && <SupportActionDialog key={action} item={item} scope={scope} action={action} onClose={() => setAction(null)} onDraft={onDraft} />}
  </div>;
}

function SupportContext({ item, scope, setAction }: { item: SupportCase; scope: SupportScope; setAction: (action: SupportAction) => void }) {
  const { t } = useI18n();
  if (!scope.platform) return <Card padding="md" className="space-y-3">
    <div className="flex flex-wrap items-center gap-3"><span className="font-semibold">{item.number}</span><SupportStatusBadge status={item.status} /><span className="text-sm text-platforma-subtle">{t(`supportCases.source.${item.source}`)}</span></div>
    <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
      <div><dt className="text-xs text-platforma-subtle">{t("supportCases.clinic")}</dt><dd className="mt-1 break-words">{item.business_name}</dd></div>
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
  </Card>;
  return <Card variant="outlined" padding="md" className="space-y-3" data-testid="support-case-context">
    <div className="flex flex-wrap items-center justify-between gap-2"><span className="text-xs text-platforma-subtle">{item.number}</span><SupportStatusBadge status={item.status} /></div>
    <dl className={scope.platform ? "space-y-3 text-sm" : "grid gap-3 text-sm sm:grid-cols-2"}>
      <div><dt className="text-xs text-platforma-subtle">{t("supportCases.clinic")}</dt><dd className="mt-1 break-words">{scope.platform ? <Link to={`/platform/merchants/${item.business}`} className="platforma-focus-ring font-medium text-brand-700">{item.business_name}</Link> : item.business_name}</dd></div>
      <div><dt className="text-xs text-platforma-subtle">{t("supportCases.assignee")}</dt><dd className="mt-1 break-words">{item.assignee?.name || t("supportCases.filter.unassigned")}</dd>{item.assignee?.available === false && <p className="mt-1 text-xs text-platforma-warning">{t("supportCases.assigneeUnavailable")}</p>}</div>
    </dl>
    <div className="flex flex-wrap gap-2">
      {item.available_actions.assign && <Button variant="secondary" onClick={() => setAction("assign")}>{t("supportCases.assign")}</Button>}
      {item.available_actions.transitions.map(status => <Button key={status} variant={status === "resolved" ? "primary" : "secondary"} onClick={() => setAction(status)}>{t(`supportCases.action.${status}`)}</Button>)}
      {item.available_actions.reopen && <Button variant="secondary" onClick={() => setAction("reopen")}>{t("supportCases.reopen")}</Button>}
    </div>
    <details className="border-t border-platforma-border pt-2 text-xs text-platforma-subtle">
      <summary className="platforma-focus-ring cursor-pointer rounded-control py-1">{t(`supportCases.source.${item.source}`)} · {item.business_timezone}</summary>
      <dl className="mt-2 grid gap-2"><div><dt>{t("supportCases.author")}</dt><dd className="break-words">{item.author.name}</dd></div><div><dt>{t("supportCases.contact")}</dt><dd className="break-words">{item.contact.name}</dd></div></dl>
    </details>
  </Card>;
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

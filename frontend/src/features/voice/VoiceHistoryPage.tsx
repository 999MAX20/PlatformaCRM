import { useInfiniteQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { Link, useSearchParams } from "react-router";
import { aiConversationsApi } from "../../api/aiConversations";
import { Button } from "../../components/ui/Button";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { formatDateTime } from "../../lib/format";
import { useI18n } from "../../lib/i18n";
import { useAuth } from "../auth/AuthProvider";
import { usePageHeader } from "../../components/layout/PageHeaderContext";
import { VoiceTurnResult } from "./VoiceTurnResult";

export default function VoiceHistoryPage() {
  const { user } = useAuth(); const { business } = useActiveBusiness(); const { t, language } = useI18n();
  const { setPageHeader } = usePageHeader();
  useEffect(() => { setPageHeader({ title: t("voice.history") }); return () => setPageHeader(null); }, [setPageHeader, t]);
  const [params] = useSearchParams(); const selected = params.get("conversation") || "";
  const locale = language === "kk" ? "kk-KZ" : language === "en" ? "en-US" : "ru-RU";
  const date = (value: string) => formatDateTime(value, business?.timezone, true, locale);
  const list = useInfiniteQuery({ queryKey: ["voice-history", user?.id, business?.id], enabled: !!user && !!business,
    initialPageParam: 0, queryFn: ({ pageParam }) => aiConversationsApi.listVoice({ business: business!.id, offset: pageParam }),
    getNextPageParam: page => page.next_offset ?? undefined });
  const detail = useInfiniteQuery({ queryKey: ["voice-history", user?.id, business?.id, selected], enabled: !!selected && !!user && !!business,
    initialPageParam: undefined as number | undefined, queryFn: async ({ pageParam }) => {
      const page = await aiConversationsApi.get(selected, pageParam);
      if (page.conversation.business !== business!.id || page.conversation.kind !== "voice") throw new Error("voice_context_unavailable");
      return page;
    }, getNextPageParam: page => page.has_more ? page.next_before ?? undefined : undefined,
    refetchInterval: query => ["preparing", "executing"].includes(query.state.data?.pages[0]?.turns.at(-1)?.status || "") ? 1500 : false });
  const conversations = list.isError ? [] : list.data?.pages.flatMap(page => page.results) || [];
  const turns = detail.isError ? [] : [...(detail.data?.pages || [])].reverse().flatMap(page => page.turns);
  return <div className="space-y-5" data-testid="voice-history">
    <h1 className="text-xl font-semibold text-platforma-text">{t("voice.history")}</h1>
    <div className="grid min-w-0 gap-5 lg:grid-cols-[minmax(220px,300px)_minmax(0,1fr)]">
      <nav aria-label={t("voice.requests")} className={`min-w-0 space-y-3 ${selected ? "hidden lg:block" : ""}`}>
        {list.isLoading && <LoadingState />}
        {list.error && <ErrorState error={list.error} action={<Button onClick={() => list.refetch()}>{t("common.retry")}</Button>} />}
        {!list.isLoading && !list.isError && !conversations.length && <EmptyState title={t("voice.historyEmpty")} />}
        <ul className="divide-y divide-platforma-border rounded-control border border-platforma-border bg-surface-card empty:hidden">
          {conversations.map(thread => <li key={thread.id}><Link to={`?conversation=${encodeURIComponent(thread.id)}`}
            aria-current={selected === thread.id ? "page" : undefined}
            className={`platforma-focus-ring block space-y-1 rounded-control px-3 py-3 ${selected === thread.id ? "bg-surface-muted" : "hover:bg-surface-muted"}`}>
            <span className="line-clamp-2 break-words text-sm font-medium">{thread.title || t("voice.request")}</span>
            <span className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-platforma-subtle"><time dateTime={thread.updated_at}>{date(thread.updated_at)}</time>
              <span>{thread.status === "empty" ? t("voice.noResult") : t(`agentChat.status.${thread.status}`)}</span></span>
          </Link></li>)}
        </ul>
        {list.hasNextPage && <Button variant="secondary" disabled={list.isFetchingNextPage} onClick={() => list.fetchNextPage()}>{t("voice.moreRequests")}</Button>}
      </nav>
      <section className="min-w-0 space-y-4" aria-label={t("voice.results")}>
        {selected && <Link to="/app/voice/history" className="platforma-focus-ring inline-flex min-h-10 items-center text-sm underline lg:hidden">{t("voice.requests")}</Link>}
        {!selected ? <p className="py-3 text-sm text-platforma-subtle">{t("voice.selectRequest")}</p> : <>
          {detail.isLoading && <LoadingState />}
          {detail.error && <ErrorState error={detail.error} action={<Button onClick={() => detail.refetch()}>{t("common.retry")}</Button>} />}
          {detail.hasNextPage && <Button variant="secondary" disabled={detail.isFetchingNextPage} onClick={() => detail.fetchNextPage()}>{t("voice.earlierMessages")}</Button>}
          {turns.map(turn => <article key={turn.id} className="space-y-4 rounded-card border border-platforma-border bg-surface-card p-4 sm:p-5">
            <header className="flex flex-wrap items-center justify-between gap-2 text-xs text-platforma-subtle">
              <time dateTime={turn.created_at}>{date(turn.created_at)}</time><span>{t(`agentChat.status.${turn.status}`)}</span>
            </header>
            {!turn.redacted && <p className="whitespace-pre-wrap break-words text-sm leading-6">{turn.message}</p>}
            <VoiceTurnResult turn={turn} readOnly busy={false} canExecute={false} onAction={() => undefined} />
          </article>)}
          {!detail.isLoading && !detail.isError && !turns.length && <EmptyState title={t("voice.noResult")} />}
        </>}
      </section>
    </div>
  </div>;
}

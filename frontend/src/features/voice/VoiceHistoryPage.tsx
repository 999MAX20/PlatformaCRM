import { useInfiniteQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { CalendarDays } from "lucide-react";
import { Link, useSearchParams } from "react-router";
import { aiConversationsApi } from "../../api/aiConversations";
import { Button } from "../../components/ui/Button";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { dateInTimeZone, formatDateTime } from "../../lib/format";
import { useI18n } from "../../lib/i18n";
import { useAuth } from "../auth/AuthProvider";
import { usePageHeader } from "../../components/layout/PageHeaderContext";
import { VoiceTurnResult } from "./VoiceTurnResult";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { historyCopy } from "./historyCopy";
import { reviewValue } from "../assistant/reviewValue";
import { DatePickerPanel, isCalendarDate } from "../../components/ui/DateRangePicker";

export default function VoiceHistoryPage() {
  const { user } = useAuth(); const { business } = useActiveBusiness(); const { t, language } = useI18n();
  const { setPageHeader } = usePageHeader();
  useEffect(() => { setPageHeader({ title: t("voice.history") }); return () => setPageHeader(null); }, [setPageHeader, t]);
  const [params, setParams] = useSearchParams(); const selected = params.get("conversation") || "";
  const copy = historyCopy[language];
  const search = params.get("search") || ""; const status = params.get("status") || "";
  const from = params.get("from") || ""; const to = params.get("to") || "";
  const calendarAnchor = useRef<HTMLButtonElement>(null);
  const [calendarOpen, setCalendarOpen] = useState(false);
  const closeCalendar = (restore = true) => { setCalendarOpen(false); if (restore) calendarAnchor.current?.focus(); };
  const periodDate = (value: string) => isCalendarDate(value) ? new Intl.DateTimeFormat(language, { day: "numeric", month: "numeric", year: "numeric", timeZone: "UTC" }).format(new Date(`${value}T12:00:00Z`)) : value;
  const periodLabel = from && to ? `${periodDate(from)} – ${periodDate(to)}` : from ? `${copy.from} ${periodDate(from)}` : to ? `${copy.to} ${periodDate(to)}` : t("timeline.chooseDate");
  const filtered = Boolean(search || status || from || to);
  const invalidDates = Boolean(from && to && from > to);
  function filter(key: string, value: string) {
    setParams(previous => { const next = new URLSearchParams(previous); next.delete("conversation");
      if (value) next.set(key, value); else next.delete(key); return next; }, { replace: true });
  }
  function selection(id?: string) {
    const next = new URLSearchParams(params); if (id) next.set("conversation", id); else next.delete("conversation");
    return `?${next.toString()}`;
  }
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
  useEffect(() => {
    if (filtered && !invalidDates && list.hasNextPage && !list.isFetching && !list.isError) void list.fetchNextPage();
  }, [filtered, invalidDates, list.hasNextPage, list.isFetching, list.isError, list.fetchNextPage]);
  const searching = filtered && !invalidDates && (list.isFetching || Boolean(list.hasNextPage)) && !list.isError;
  const localDay = (value: string) => dateInTimeZone(value, business?.timezone || "UTC");
  const conversations = (list.isError ? [] : list.data?.pages.flatMap(page => page.results) || []).filter(thread => {
    const day = localDay(thread.updated_at);
    return !invalidDates && thread.title.toLocaleLowerCase(locale).includes(search.trim().toLocaleLowerCase(locale))
      && (!status || thread.status === status) && (!from || day >= from) && (!to || day <= to);
  });
  const turns = detail.isError ? [] : [...(detail.data?.pages || [])].reverse().flatMap(page => page.turns);
  return <div className="space-y-5" data-testid="voice-history">
    <h1 className="sr-only">{t("voice.history")}</h1>
    <div className="grid grid-cols-2 items-end gap-3 sm:flex sm:flex-wrap">
      <div className="col-span-2 min-w-0 sm:w-[var(--global-search-width,480px)]"><Input label={copy.search} type="search" value={search} onChange={event => filter("search", event.target.value)} /></div>
      <div className="col-span-2 min-w-0 sm:w-72">
      <Select label={copy.status} portal className="h-auto min-h-11 py-2 [&>span]:whitespace-normal [&>span]:overflow-visible [&>span]:text-left" value={status} onChange={event => filter("status", event.target.value)} options={[
        { value: "", label: copy.all }, ...["preparing", "clarifying", "awaiting_confirmation", "executing", "completed", "failed", "cancelled", "superseded", "empty"].map(value => ({ value, label: t(value === "empty" ? "voice.noResult" : `agentChat.status.${value}`) }))]} />
      </div>
      <Button ref={calendarAnchor} data-calendar-trigger type="button" variant="secondary" className="col-span-2 min-h-11 min-w-0 max-w-full" aria-label={t("timeline.chooseDate")} aria-haspopup="dialog" aria-expanded={calendarOpen} onClick={() => setCalendarOpen(value => !value)}>
        <CalendarDays size={17} className="shrink-0" /><span className="whitespace-normal">{periodLabel}</span>
      </Button>
      {calendarOpen && <DatePickerPanel anchor={calendarAnchor} label={t("timeline.chooseDate")} value={{ from, to }} today={dateInTimeZone(new Date(), business?.timezone || "UTC")} allowClear onApply={range => {
        setParams(previous => { const next = new URLSearchParams(previous); next.delete("conversation");
          for (const key of ["from", "to"] as const) { if (range[key]) next.set(key, range[key]); else next.delete(key); } return next; }, { replace: true });
        closeCalendar();
      }} onClose={closeCalendar} />}
      {filtered && <Button variant="ghost" onClick={() => setParams({})}>{copy.reset}</Button>}
    </div>
    {invalidDates && <p role="alert" className="text-sm text-platforma-danger">{copy.dates}</p>}
    <div className="grid min-w-0 items-start gap-5 lg:grid-cols-[minmax(260px,360px)_minmax(0,1fr)]">
      <nav aria-label={t("voice.requests")} className={`min-w-0 space-y-3 ${selected ? "hidden lg:block" : ""}`}>
        {list.isLoading && <LoadingState />}
        {searching && <p role="status" className="text-sm text-platforma-subtle">{copy.loading}</p>}
        {list.error && <ErrorState error={list.error} action={<Button onClick={() => list.refetch()}>{t("common.retry")}</Button>} />}
        {!list.isLoading && !searching && !list.isError && !conversations.length && <EmptyState title={filtered ? copy.empty : t("voice.historyEmpty")} />}
        <div className="overflow-hidden rounded-control border border-platforma-border bg-surface-card">
        <h2 className="border-b border-platforma-border px-4 py-3 text-base font-semibold">{t("voice.requests")}</h2>
        <ul className="divide-y divide-platforma-border empty:hidden">
          {conversations.map((thread, index) => <li key={thread.id}>
            {(index === 0 || localDay(conversations[index - 1].updated_at) !== localDay(thread.updated_at)) && <p className="border-b border-platforma-border px-4 py-2 text-sm font-medium text-platforma-subtle">
              {new Intl.DateTimeFormat(locale, { timeZone: business?.timezone || "UTC", day: "numeric", month: language === "kk" ? "2-digit" : "long", year: "numeric" }).format(new Date(thread.updated_at))}
            </p>}
            <Link to={selection(thread.id)}
            aria-current={selected === thread.id ? "page" : undefined}
            className={`platforma-focus-ring block space-y-1 rounded-control px-3 py-3 ${selected === thread.id ? "bg-surface-muted" : "hover:bg-surface-muted"}`}>
            <span className="line-clamp-2 break-words text-sm font-medium">{thread.title || t("voice.request")}</span>
            <span className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-platforma-subtle"><time dateTime={thread.updated_at}>{date(thread.updated_at)}</time>
              <span>{thread.status === "empty" ? t("voice.noResult") : t(`agentChat.status.${thread.status}`)}</span></span>
          </Link></li>)}
        </ul>
        </div>
        {list.hasNextPage && !filtered && <Button variant="secondary" disabled={list.isFetchingNextPage} onClick={() => list.fetchNextPage()}>{t("voice.moreRequests")}</Button>}
      </nav>
      <section className="min-w-0 space-y-4" aria-label={t("voice.results")}>
        {selected && <Link to={selection()} className="platforma-focus-ring inline-flex min-h-11 items-center text-sm underline lg:hidden">{t("voice.requests")}</Link>}
        {!selected ? <p className="py-3 text-sm text-platforma-subtle">{t("voice.selectRequest")}</p> : <>
          {detail.isLoading && <LoadingState />}
          {detail.error && <ErrorState error={detail.error} action={<Button onClick={() => detail.refetch()}>{t("common.retry")}</Button>} />}
          {detail.hasNextPage && <Button variant="secondary" disabled={detail.isFetchingNextPage} onClick={() => detail.fetchNextPage()}>{t("voice.earlierMessages")}</Button>}
          {turns.map(turn => <article key={turn.id} className="space-y-4 rounded-card border border-platforma-border bg-surface-card p-4 sm:p-5">
            <header className="flex flex-wrap items-center justify-between gap-2 text-xs text-platforma-subtle">
              <time dateTime={turn.created_at}>{date(turn.created_at)}</time><span>{t(`agentChat.status.${turn.status}`)}</span>
            </header>
            <h2 className="text-lg font-semibold">{copy.result}</h2>
            <div className="rounded-control border border-platforma-border bg-surface-muted p-4">
              <VoiceTurnResult turn={{ ...turn, actions: turn.actions.map(action => action.tool_name === "crm_schedule" ? action : {
                ...action, input_json: { ...action.input_json,
                  ...Object.fromEntries((["values", "before"] as const).map(side => [side,
                    Object.fromEntries(Object.entries((action.input_json[side] || {}) as Record<string, unknown>).map(([key, value]) =>
                      [key, reviewValue(key, value, side, action.review, language, t("aiCRM.referenceUnavailable"))]))])),
                },
              }) }} readOnly busy={false} canExecute={false} onAction={() => undefined} />
              {!turn.redacted && <div className="mt-3 space-y-2 text-sm text-platforma-subtle">
                {turn.status === "clarifying" && <p>{copy.clarification}</p>}
                {turn.status === "awaiting_confirmation" && <p>{copy.pending}</p>}
                {turn.total_steps > 0 && <p>{copy.progress}: {turn.completed_steps} / {turn.total_steps}</p>}
                {turn.status === "completed" && !turn.actions.some(action => action.status === "executed") && <p>{copy.noActions}</p>}
              </div>}
            </div>
            {!turn.redacted && <section className="space-y-3 border-t border-platforma-border pt-4">
              <h3 className="text-base font-semibold">{copy.original}</h3>
              <p className="whitespace-pre-wrap break-words text-sm leading-6">{turn.message}</p>
            </section>}
          </article>)}
          {!detail.isLoading && !detail.isError && !turns.length && <EmptyState title={t("voice.noResult")} />}
        </>}
      </section>
    </div>
  </div>;
}

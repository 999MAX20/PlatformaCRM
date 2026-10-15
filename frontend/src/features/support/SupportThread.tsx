import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { LockKeyhole } from "lucide-react";
import { supportApi } from "../../api/support";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { LoadingState } from "../../components/ui/StateViews";
import { Textarea } from "../../components/ui/Textarea";
import { useI18n } from "../../lib/i18n";
import type { SupportCase, SupportMessage, SupportNote, SupportPage, SupportScope } from "../../types/support";
import { SupportError, supportDate, useSupportKey } from "./SupportUI";

export type SupportDraftListener = (name: string, dirty: boolean, pending: boolean) => void;

export function SupportPager({ page, total, pageSize, onChange }: { page: number; total: number; pageSize: number; onChange: (page: number) => void }) {
  const { t } = useI18n();
  const pages = Math.max(1, Math.ceil(total / pageSize));
  if (pages === 1) return null;
  return <div className="flex flex-wrap items-center justify-between gap-2 border-t border-platforma-border pt-3">
    <Button variant="ghost" disabled={page <= 1} onClick={() => onChange(page - 1)}>{t("pagination.previous")}</Button>
    <span className="text-xs text-platforma-subtle">{t("supportCases.page", { page, pages })}</span>
    <Button variant="ghost" disabled={page >= pages} onClick={() => onChange(page + 1)}>{t("pagination.next")}</Button>
  </div>;
}

export function SupportThread({ item, scope, internal = false, active = true, onDraft }: {
  item: SupportCase; scope: SupportScope; internal?: boolean; active?: boolean; onDraft: SupportDraftListener;
}) {
  const { t, language } = useI18n();
  const queryClient = useQueryClient();
  const mode = scope.platform ? "platform" : "clinic";
  const kind = internal ? "notes" : "messages";
  const [page, setPage] = useState(1);
  const [text, setText] = useState("");
  const key = useSupportKey();
  const attemptedRead = useRef(0);
  const thread = useQuery({
    queryKey: ["support", mode, scope.business, kind, item.id, page],
    queryFn: (): Promise<SupportPage<SupportMessage | SupportNote>> => internal ? supportApi.notes(item.id, page) : supportApi.messages(scope, item.id, page),
    refetchInterval: 30_000,
  });
  const send = useMutation({
    mutationFn: () => internal ? supportApi.addNote(item.id, text.trim(), key.forPayload(text.trim())) : supportApi.reply(scope, item.id, text.trim(), key.forPayload(text.trim())),
    onSuccess: () => {
      setText(""); setPage(1); key.reset();
      queryClient.invalidateQueries({ queryKey: ["support", mode] });
    },
  });
  const read = useMutation({
    mutationFn: (id: number) => supportApi.markRead(scope, item.id, id),
    onSuccess: () => {
      queryClient.invalidateQueries({ predicate: query => query.queryKey[0] === "support" && query.queryKey[1] === mode && ["case", "list"].includes(String(query.queryKey[3])) });
    },
  });
  const latest = thread.data?.results[0]?.id || 0;
  useEffect(() => {
    onDraft(kind, Boolean(text.trim()), send.isPending);
  }, [kind, text, send.isPending, onDraft]);
  useEffect(() => {
    if (!active || internal || page !== 1 || thread.isError || thread.isFetching || latest <= attemptedRead.current) return;
    attemptedRead.current = latest;
    if (latest) read.mutate(latest);
  }, [active, internal, latest, page, thread.isError, thread.isFetching]);
  const messages = thread.data?.results || [];
  return <Card padding="md" variant={internal ? "muted" : scope.platform ? "outlined" : "default"} className="min-w-0 space-y-4" data-testid={internal ? "support-internal-notes" : "support-public-thread"}>
    <div><h2 className="flex items-center gap-2 font-semibold">{internal && <LockKeyhole size={16} aria-hidden="true" />}{t(internal ? "supportCases.internalNotes" : "supportCases.publicThread")}</h2>{internal && <p className="mt-1 text-xs text-platforma-subtle">{t("supportCases.internalOnly")}</p>}</div>
    {thread.isPending ? <LoadingState /> : thread.isError ? <SupportError error={thread.error} retry={() => thread.refetch()} /> : !messages.length ? <p className="text-sm text-platforma-subtle">{t(internal ? "supportCases.noNotes" : "supportCases.noMessages")}</p> : <div className="space-y-3">
      {(internal ? messages : [...messages].reverse()).map(message => <article key={message.id} className="rounded-control border border-platforma-border bg-surface-card p-3">
        <header className="flex flex-wrap items-start justify-between gap-1 text-xs text-platforma-subtle"><span className="break-words font-semibold">{message.author.name}</span><time dateTime={message.created_at}>{supportDate(message.created_at, language, item.business_timezone)}</time></header>
        <p className="mt-2 whitespace-pre-wrap text-sm leading-6 [overflow-wrap:anywhere]">{message.text}</p>
      </article>)}
    </div>}
    {thread.data && <SupportPager page={page} total={thread.data.count} pageSize={internal ? 10 : 20} onChange={setPage} />}
    {!internal && read.isError && <SupportError error={read.error} retry={() => read.mutate(latest)} />}
    <form className="space-y-3 border-t border-platforma-border pt-4" onSubmit={event => { event.preventDefault(); send.mutate(); }}>
      <Textarea label={t(internal ? "supportCases.internalText" : scope.platform ? "supportCases.replyClinic" : "supportCases.replySupport")} value={text} onChange={event => setText(event.target.value)} maxLength={6000} required disabled={send.isPending} />
      {send.isError && <SupportError error={send.error} />}
      <div className="flex justify-end"><Button type="submit" variant={internal ? "secondary" : "primary"} disabled={!text.trim()} isLoading={send.isPending}>{t(internal ? "supportCases.saveNote" : "supportCases.sendReply")}</Button></div>
    </form>
  </Card>;
}

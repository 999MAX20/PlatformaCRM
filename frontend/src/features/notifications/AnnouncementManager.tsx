import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { notificationsApi } from "../../api/notifications";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { Select } from "../../components/ui/Select";
import { Textarea } from "../../components/ui/Textarea";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useActionFeedback } from "../../components/actions/useActionFeedback";
import { formatDateTime } from "../../lib/format";
import { useI18n } from "../../lib/i18n";
import { realtimeIntervals } from "../../lib/realtime";
import { useAuth } from "../auth/AuthProvider";
import type { Id, Notification } from "../../types";
import { useAnnouncementEvents } from "./useAnnouncementEvents";

export function NotificationPagination({ page, previous, next, onPage }: {
  page: number; previous: boolean; next: boolean; onPage: (page: number) => void;
}) {
  const { t } = useI18n();
  return previous || next ? <nav aria-label={t("notification.pages")} className="flex items-center justify-end gap-3">
    <Button variant="secondary" disabled={!previous} onClick={() => onPage(page - 1)}>{t("notification.previous")}</Button>
    <span className="text-sm text-platforma-subtle">{page}</span>
    <Button variant="secondary" disabled={!next} onClick={() => onPage(page + 1)}>{t("notification.next")}</Button>
  </nav> : null;
}

export function AnnouncementManager({ business }: { business: Id }) {
  const { t, language } = useI18n();
  const { user } = useAuth();
  const client = useQueryClient();
  const feedback = useActionFeedback();
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);
  const [monitor, setMonitor] = useState<Id | null>(null);
  const announcements = useQuery({ queryKey: ["announcements", business, user?.id, page],
    queryFn: () => notificationsApi.announcements(business, page), refetchInterval: realtimeIntervals.notificationsMs,
    refetchOnWindowFocus: true, retry: false });
  useAnnouncementEvents(business, user?.id, !announcements.isError && Boolean(announcements.data?.events_enabled));
  return <section className="space-y-4">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <h2 className="text-lg font-semibold text-platforma-ink">{t("notification.announcements")}</h2>
      <Button onClick={() => setCreating(true)}>{t("notification.publishAnnouncement")}</Button>
    </div>
    {announcements.isPending ? <LoadingState /> : announcements.isError ? <ErrorState error={announcements.error}
      action={<Button variant="secondary" onClick={() => void announcements.refetch()}>{t("common.retry")}</Button>} /> : <>
      {announcements.data?.results.map(row => <article key={row.id} className="space-y-3 rounded-card border border-platforma-border bg-surface-card p-4">
        <p className="line-clamp-3 whitespace-pre-wrap break-words text-sm font-semibold text-platforma-ink">{row.text}</p>
        <p className="text-xs text-platforma-subtle">{row.author_name} · {formatDateTime(row.created_at, undefined, false, language)}{row.revoked_at ? ` · ${t("notification.revoked")}` : ""}</p>
        <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
          {([ ["recipient_count", "notification.recipients"], ["opened_count", "notification.opened"],
            ["read_count", "notification.readCount"], ["acknowledged_count", "notification.acknowledged"] ] as const).map(([field, key]) =>
            <div key={field}><dt className="text-platforma-subtle">{t(key)}</dt><dd className="font-semibold text-platforma-ink">{row[field]}</dd></div>)}
        </dl>
        <Button variant="secondary" onClick={() => setMonitor(row.id)}>{t("notification.monitoring")}</Button>
      </article>)}
      {!announcements.data?.results.length ? <EmptyState title={t("notification.noAnnouncements")} /> : null}
      <NotificationPagination page={page} previous={Boolean(announcements.data?.previous)} next={Boolean(announcements.data?.next)} onPage={setPage} />
    </>}
    {creating ? <AnnouncementComposer business={business} onClose={() => setCreating(false)} onPublished={() => {
      setCreating(false); setPage(1);
      feedback.notifySuccess(t("notification.published"));
      void client.invalidateQueries({ queryKey: ["announcements"] });
      void client.invalidateQueries({ queryKey: ["notifications"] });
      void client.invalidateQueries({ queryKey: ["notifications-summary"] });
    }} /> : null}
    {monitor ? <AnnouncementMonitor key={String(monitor)} business={business} id={monitor} onClose={() => setMonitor(null)} /> : null}
  </section>;
}

function AnnouncementComposer({ business, onClose, onPublished }: { business: Id; onClose: () => void; onPublished: () => void }) {
  const { t } = useI18n();
  const [text, setText] = useState("");
  const [priority, setPriority] = useState<Notification["priority"]>("normal");
  // Reuse the exact command after an uncertain network outcome; editing the
  // content starts a new command instead of silently reusing another payload.
  const [publicationKey, setPublicationKey] = useState(() => crypto.randomUUID());
  const publish = useMutation({ mutationFn: () => notificationsApi.publish(business, { text, priority, publication_key: publicationKey }), onSuccess: onPublished });
  const resetCommand = () => { setPublicationKey(crypto.randomUUID()); publish.reset(); };
  return <Modal title={t("notification.publishAnnouncement")} open onClose={() => { if (!publish.isPending) onClose(); }} testId="announcement-composer">
    <form className="space-y-4" onSubmit={event => { event.preventDefault(); publish.mutate(); }}>
      <p className="text-sm text-platforma-subtle">{t("notification.audienceAll")}</p>
      <Textarea label={t("notification.announcementText")} value={text} maxLength={4000} required disabled={publish.isPending}
        onChange={event => { setText(event.target.value); resetCommand(); }} />
      <Select label={t("notification.priorityLabel")} value={priority} disabled={publish.isPending}
        options={(["low", "normal", "high", "urgent"] as const).map(value => ({ value, label: t(`notification.priority.${value}`) }))}
        onChange={event => { setPriority(event.target.value as Notification["priority"]); resetCommand(); }} />
      {publish.isError ? <ErrorState error={publish.error} /> : null}
      <div className="flex flex-wrap justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onClose} disabled={publish.isPending}>{t("common.cancel")}</Button>
        <Button type="submit" disabled={!text.trim()} isLoading={publish.isPending}>{t("notification.publish")}</Button>
      </div>
    </form>
  </Modal>;
}

function AnnouncementMonitor({ business, id, onClose }: { business: Id; id: Id; onClose: () => void }) {
  const { t, language } = useI18n();
  const { user } = useAuth();
  const client = useQueryClient();
  const [page, setPage] = useState(1);
  const [confirmRevoke, setConfirmRevoke] = useState(false);
  const monitoring = useQuery({ queryKey: ["announcements", "recipients", business, user?.id, id, page],
    queryFn: () => notificationsApi.recipients(id, business, page), refetchInterval: realtimeIntervals.notificationsMs,
    refetchOnWindowFocus: true, retry: false });
  const revoke = useMutation({ mutationFn: () => notificationsApi.revoke(id, business), onSuccess: () => {
    setConfirmRevoke(false);
    void client.invalidateQueries({ queryKey: ["announcements"] });
    void client.invalidateQueries({ queryKey: ["notifications"] });
    void client.invalidateQueries({ queryKey: ["notifications-summary"] });
  }, onError: () => { void monitoring.refetch(); } });
  const timestamp = (value: string | null) => value ? formatDateTime(value, undefined, false, language) : t("notification.notYet");
  return <Modal title={t("notification.monitoring")} open onClose={onClose} size="lg" testId="announcement-monitor">
    {monitoring.isPending ? <LoadingState /> : monitoring.isError ? <ErrorState error={monitoring.error}
      action={<Button variant="secondary" onClick={() => void monitoring.refetch()}>{t("common.retry")}</Button>} /> : monitoring.data ? <div className="space-y-4">
      <p className="whitespace-pre-wrap break-words text-sm text-platforma-ink">{monitoring.data.announcement.text}</p>
      {monitoring.data.announcement.revoked_at ? <p role="status" className="text-sm text-platforma-subtle">{t("notification.revoked")} · {formatDateTime(monitoring.data.announcement.revoked_at, undefined, false, language)}</p> : null}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead><tr className="border-b border-platforma-border text-platforma-subtle">
            {["notification.employee", "notification.opened", "notification.readCount", "notification.acknowledged"].map(key => <th key={key} scope="col" className="px-3 py-2 font-semibold">{t(key)}</th>)}
          </tr></thead>
          <tbody>{monitoring.data.results.map(row => <tr key={row.id} className="border-b border-platforma-border">
            <th scope="row" className="px-3 py-3 font-medium text-platforma-ink">{row.name}</th>
            <td className="px-3 py-3 text-platforma-subtle">{timestamp(row.opened_at)}</td>
            <td className="px-3 py-3 text-platforma-subtle">{timestamp(row.read_at)}</td>
            <td className="px-3 py-3 text-platforma-subtle">{timestamp(row.acknowledged_at)}</td>
          </tr>)}</tbody>
        </table>
      </div>
      {!monitoring.data.results.length ? <EmptyState title={t("notification.noRecipients")} /> : null}
      <NotificationPagination page={page} previous={Boolean(monitoring.data.previous)} next={Boolean(monitoring.data.next)} onPage={setPage} />
      {revoke.isError ? <ErrorState error={revoke.error} /> : null}
      {!monitoring.data.announcement.revoked_at ? confirmRevoke ? <div className="space-y-3 rounded-control border border-platforma-border p-3">
        <p className="text-sm text-platforma-ink">{t("notification.revokeQuestion")}</p>
        <div className="flex flex-wrap gap-2">
          <Button variant="danger" onClick={() => revoke.mutate()} isLoading={revoke.isPending}>{t("notification.revoke")}</Button>
          <Button variant="secondary" onClick={() => setConfirmRevoke(false)} disabled={revoke.isPending}>{t("common.cancel")}</Button>
        </div>
      </div> : <Button variant="secondary" onClick={() => setConfirmRevoke(true)}>{t("notification.revoke")}</Button> : null}
    </div> : null}
  </Modal>;
}

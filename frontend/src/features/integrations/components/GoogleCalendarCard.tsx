import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { googleIntegrationsApi } from "../../../api/googleIntegrations";
import { googleCalendarApi, type GoogleCalendarBinding } from "../../../api/googleCalendar";
import { Button } from "../../../components/ui/Button";
import { Modal } from "../../../components/ui/Modal";
import { Select } from "../../../components/ui/Select";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import { useAuth } from "../../auth/AuthProvider";
import type { Id } from "../../../types";

export function GoogleCalendarCard({ businessId }: { businessId: Id }) {
  const { user } = useAuth();
  const { t, language } = useI18n();
  const cache = useQueryClient();
  const [dialog, setDialog] = useState<"bind" | "disconnect" | "pause" | null>(null);
  const [resource, setResource] = useState("");
  const [calendar, setCalendar] = useState("");
  const [selected, setSelected] = useState<GoogleCalendarBinding | null>(null);
  const [revokeFailed, setRevokeFailed] = useState(false);
  const key = ["google-calendar", user?.id, businessId];
  const connection = useQuery({ queryKey: [...key, "connection"],
    queryFn: () => googleIntegrationsApi.status(businessId, "google_calendar") });
  const id = connection.data?.id;
  const connected = connection.data?.status === "connected";
  const bindings = useQuery({ queryKey: [...key, id, "bindings"],
    queryFn: () => googleCalendarApi.bindings(id!), enabled: Boolean(id && connected), refetchInterval: connected ? 5000 : false });
  const calendars = useQuery({ queryKey: [...key, id, "calendars"], queryFn: () => googleCalendarApi.calendars(id!),
    enabled: Boolean(id && connected && dialog === "bind") });
  const reload = () => cache.invalidateQueries({ queryKey: key });
  const connect = useMutation({ mutationFn: () => googleIntegrationsApi.start(businessId, "google_calendar"),
    onSuccess: result => window.location.assign(result.authorization_url) });
  const bind = useMutation({ mutationFn: () => googleCalendarApi.bind(id!, Number(resource), calendar),
    onSuccess: async () => { setDialog(null); setResource(""); setCalendar(""); await reload(); } });
  const toggle = useMutation({ mutationFn: (item: GoogleCalendarBinding) => googleCalendarApi.enabled(id!, item.id, !item.enabled),
    onSuccess: async () => { setDialog(null); await reload(); } });
  const sync = useMutation({ mutationFn: (bindingId: string) => googleCalendarApi.sync(id!, bindingId), onSuccess: reload });
  const disconnect = useMutation({ mutationFn: () => googleIntegrationsApi.disconnect(id!),
    onSuccess: async result => { setDialog(null); setRevokeFailed(!result.google_revoked); await reload(); } });
  const busy = connect.isPending || bind.isPending || toggle.isPending || sync.isPending || disconnect.isPending;
  const prefix = `google-calendar-${businessId}`;
  const error = connection.error || bindings.error || connect.error || toggle.error || sync.error;
  const requestedBinding = bindings.data?.bindings.find(item => item.id === sync.variables);
  const refreshPending = sync.isSuccess && requestedBinding && (!requestedBinding.last_sync_at
    || new Date(requestedBinding.last_sync_at).getTime() < sync.submittedAt);
  return <section className="min-w-0 space-y-4 rounded-card border border-platforma-border bg-surface-card p-4" aria-label="Google Calendar">
    <h2 className="font-semibold">Google Calendar</h2>
    {connection.isLoading || bindings.isLoading ? <LoadingState /> : null}
    {error ? <ErrorState error={error} action={<Button disabled={busy} onClick={() => { if (connect.error) connect.mutate(); else { toggle.reset(); sync.reset(); void reload(); } }}>{t("common.retry")}</Button>} /> : null}
    {!connected && connection.data?.enabled === false && <p role="status" className="text-sm">{t("googleCalendar.serverDisabled")}</p>}
    {!connection.isLoading && !connection.error && !connected && <Button id={`${prefix}-connect`} disabled={busy || connection.data?.enabled === false} isLoading={connect.isPending} onClick={() => connect.mutate()}>{t("googleSheets.connect")}</Button>}
    {connected && !connection.error && <>
      <p className="break-words text-sm">{connection.data?.email}</p>
      {bindings.data && !bindings.data.enabled && <p role="status" className="text-sm">{t("googleCalendar.serverDisabled")}</p>}
      <div className="flex flex-wrap gap-2">
        <Button id={`${prefix}-bind`} data-focus-return-id={`${prefix}-bind`} disabled={busy || !bindings.data?.enabled}
          onClick={() => { bind.reset(); setDialog("bind"); }}>{t("googleCalendar.add")}</Button>
        <Button id={`${prefix}-disconnect`} data-focus-return-id={`${prefix}-disconnect`} variant="ghost" disabled={busy}
          onClick={() => { disconnect.reset(); setDialog("disconnect"); }}>{t("googleSheets.disconnect")}</Button>
      </div>
      {bindings.data?.bindings.length === 0 && <p className="text-sm text-platforma-muted">{t("googleCalendar.empty")}</p>}
      {bindings.data?.bindings.map(item => <div key={item.id} className="space-y-2 border-t border-platforma-border pt-3">
        <p className="break-words text-sm font-medium">{item.resource_name}: {item.calendar_name || t("googleCalendar.calendar")}</p>
        <p className="text-sm" role="status">{t(!item.enabled ? "googleCalendar.paused" : item.error_code || (item.last_sync_at && item.stale) ? "googleCalendar.failed" : !item.last_sync_at || item.pending ? "googleCalendar.pending" : "googleCalendar.synced")}</p>
        {item.last_sync_at && <p className="text-sm text-platforma-muted">{t("googleCalendar.lastSync", { time: new Date(item.last_sync_at).toLocaleString(language) })}</p>}
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" disabled={busy || !item.enabled || !bindings.data?.enabled} onClick={() => sync.mutate(item.id)}>{t("googleCalendar.sync")}</Button>
          <Button id={`${prefix}-${item.id}`} data-focus-return-id={`${prefix}-${item.id}`} variant="ghost" disabled={busy || (!item.enabled && !bindings.data?.enabled)}
            onClick={() => { toggle.reset(); setSelected(item); if (item.enabled) setDialog("pause"); else toggle.mutate(item); }}>{t(item.enabled ? "googleCalendar.pause" : "googleCalendar.resume")}</Button>
        </div>
      </div>)}
      {refreshPending && <p role="status" className="text-sm">{t("googleCalendar.queued")}</p>}
    </>}
    {revokeFailed && <p role="alert" className="text-sm">{t("googleSheets.revokeFailed")} <a className="underline" href="https://myaccount.google.com/connections" target="_blank" rel="noopener noreferrer">{t("googleSheets.googleAccess")}</a></p>}
    <Modal open={dialog === "bind"} title={t("googleCalendar.add")} focusReturnId={`${prefix}-bind`} onClose={() => { if (!busy) setDialog(null); }}>
      <div className="space-y-4">
        {calendars.isLoading ? <LoadingState /> : null}
        {calendars.error ? <ErrorState error={calendars.error} action={<Button onClick={() => void calendars.refetch()}>{t("common.retry")}</Button>}/> : null}
        <Select label={t("googleCalendar.specialist")} value={resource} onChange={event => setResource(event.target.value)} disabled={busy}
          options={[{value: "", label: t("googleCalendar.choose")}, ...(bindings.data?.specialists.map(item => ({value: item.id, label: item.name})) ?? [])]} />
        <Select label={t("googleCalendar.calendar")} value={calendar} onChange={event => setCalendar(event.target.value)} disabled={busy || calendars.isLoading}
          options={[{value: "", label: t("googleCalendar.choose")}, ...(calendars.data?.map(item => ({value: item.id, label: `${item.name} (${item.timezone})`})) ?? [])]} />
        {calendars.data?.length === 0 && <p role="status" className="text-sm">{t("googleCalendar.noCalendars")}</p>}
        <p className="text-sm">{t("googleCalendar.confirm")}</p>
        {bind.error ? <ErrorState error={bind.error} /> : null}
        <Button disabled={busy || !resource || !calendar || Boolean(calendars.error)} isLoading={bind.isPending} onClick={() => bind.mutate()}>{t("googleCalendar.confirmConnect")}</Button>
      </div>
    </Modal>
    <Modal open={dialog === "pause"} title={t("googleCalendar.pause")} focusReturnId={`${prefix}-${selected?.id}`} onClose={() => { if (!busy) setDialog(null); }}>
      <div className="space-y-4"><p>{t("googleCalendar.pauseConfirm")}</p>{toggle.error ? <ErrorState error={toggle.error} /> : null}
        <Button disabled={busy || !selected} onClick={() => { if (selected) toggle.mutate(selected); }}>{t("googleCalendar.pause")}</Button></div>
    </Modal>
    <Modal open={dialog === "disconnect"} title={t("googleSheets.disconnect")} focusReturnId={`${prefix}-${disconnect.isSuccess ? "connect" : "disconnect"}`} onClose={() => { if (!busy) setDialog(null); }}>
      <div className="space-y-4"><p>{t("googleCalendar.disconnectConfirm")}</p>{disconnect.error ? <ErrorState error={disconnect.error} /> : null}
        {connection.data?.retention_enabled && <p>{t("googleCalendar.retentionNotice")}</p>}
        <Button variant="danger" disabled={busy} isLoading={disconnect.isPending} onClick={() => disconnect.mutate()}>{t("googleSheets.disconnect")}</Button></div>
    </Modal>
  </section>;
}

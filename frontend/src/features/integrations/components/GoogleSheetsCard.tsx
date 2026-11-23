import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { googleIntegrationsApi, type GoogleExport, type GoogleSpreadsheet } from "../../../api/googleIntegrations";
import { chooseGoogleSpreadsheet } from "../../../api/googlePicker";
import { Button } from "../../../components/ui/Button";
import { Badge } from "../../../components/ui/Badge";
import { Modal } from "../../../components/ui/Modal";
import { Select } from "../../../components/ui/Select";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import { hasPermission } from "../../../lib/permissions";
import { useAuth } from "../../auth/AuthProvider";
import type { Id, ImportJob } from "../../../types";
import { ImportJobReview } from "./ImportJobReview";

export function GoogleSheetsCard({ businessId }: { businessId: Id }) {
  const { t, language } = useI18n();
  const { user } = useAuth();
  const cache = useQueryClient();
  const [dialog, setDialog] = useState<"import" | "export" | "disconnect" | null>(null);
  const [selected, setSelected] = useState<GoogleSpreadsheet | null>(null);
  const [sheetId, setSheetId] = useState("");
  const [requestKey, setRequestKey] = useState("");
  const [job, setJob] = useState<ImportJob | null>(null);
  const [target, setTarget] = useState<GoogleExport | null>(null);
  const [revokeFailed, setRevokeFailed] = useState(false);
  const canCreate = hasPermission(user, businessId, "clients", "create");
  const canView = hasPermission(user, businessId, "clients", "view");
  const connection = useQuery({ queryKey: ["google-connection", user?.id, businessId], queryFn: () => googleIntegrationsApi.status(businessId) });
  const id = connection.data?.id;
  const connected = connection.data?.status === "connected";
  const exports = useQuery({ queryKey: ["google-exports", user?.id, businessId, id],
    queryFn: () => googleIntegrationsApi.exports(id!), enabled: Boolean(id && connected && canView) });
  const reload = async () => {
    await Promise.all([cache.invalidateQueries({ queryKey: ["google-connection", user?.id, businessId] }),
      cache.invalidateQueries({ queryKey: ["google-exports", user?.id, businessId] })]);
  };
  const connect = useMutation({ mutationFn: () => googleIntegrationsApi.start(businessId),
    onSuccess: result => { window.location.assign(result.authorization_url); } });
  const choose = useMutation({ mutationFn: async () => {
    const file = await chooseGoogleSpreadsheet(id!, language);
    return file ? googleIntegrationsApi.metadata(id!, file) : null;
  }, onSuccess: result => {
    if (!result) return;
    setSelected(result); setSheetId(String(result.sheets[0]?.sheetId ?? ""));
    setRequestKey(crypto.randomUUID()); setJob(null); snapshot.reset(); setDialog("import");
  } });
  const snapshot = useMutation({ mutationFn: () => googleIntegrationsApi.import(id!, selected!.id, Number(sheetId), requestKey), onSuccess: setJob });
  const exportMutation = useMutation({ mutationFn: () => googleIntegrationsApi.export(id!, requestKey, Boolean(target?.status === "succeeded")),
    onSuccess: async () => { await reload(); setDialog(null); }, onError: () => { void reload(); } });
  const disconnect = useMutation({ mutationFn: () => googleIntegrationsApi.disconnect(id!),
    onSuccess: async result => { setRevokeFailed(!result.google_revoked); setDialog(null); await reload(); } });
  const busy = connect.isPending || choose.isPending || snapshot.isPending || exportMutation.isPending || disconnect.isPending;
  const startExport = (existing: GoogleExport | null) => {
    setTarget(existing); setRequestKey(existing?.request_key ?? crypto.randomUUID()); exportMutation.reset(); setDialog("export");
  };
  const error = connection.error || connect.error || choose.error;
  return <section className="min-w-0 space-y-4 rounded-card border border-platforma-border bg-surface-card p-4" aria-label="Google Sheets">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <h2 className="font-semibold">Google Sheets</h2>
      {connection.data && <Badge variant={connected ? "success" : "neutral"}>{t(connected ? "integrations.status.connected" : "integrations.status.notConnected")}</Badge>}
    </div>
    {connection.isLoading ? <LoadingState /> : null}
    {error ? <ErrorState error={error} action={<Button variant="secondary" disabled={busy} onClick={() => {
      if (choose.error) choose.mutate();
      else if (connect.error) connect.mutate();
      else void connection.refetch();
    }}>{t("common.retry")}</Button>} /> : null}
    {connection.data?.email && <p className="break-all text-sm text-platforma-muted">{connection.data.email}</p>}
    {revokeFailed && <p role="alert" className="text-sm">{t("googleSheets.revokeFailed")} <a href="https://myaccount.google.com/connections" target="_blank" rel="noopener noreferrer" className="underline">{t("googleSheets.googleAccess")}</a></p>}
    {connection.data && <div className="flex flex-wrap gap-2">
      {!connected && <Button id={`google-connection-${businessId}`} data-focus-return-id={`google-connection-${businessId}`} disabled={busy} onClick={() => connect.mutate()} isLoading={connect.isPending}>{t("googleSheets.connect")}</Button>}
      {connected && <>
        {canCreate && <Button id={`google-import-${businessId}`} data-focus-return-id={`google-import-${businessId}`} disabled={busy} isLoading={choose.isPending} onClick={() => choose.mutate()}>{t("googleSheets.import")}</Button>}
        {canView && <Button id={`google-export-${businessId}`} data-focus-return-id={`google-export-${businessId}`} disabled={busy} variant="secondary" onClick={() => startExport(null)}>{t("googleSheets.export")}</Button>}
        <Button id={`google-connection-${businessId}`} data-focus-return-id={`google-connection-${businessId}`} disabled={busy} variant="ghost" onClick={() => { disconnect.reset(); setDialog("disconnect"); }}>{t("googleSheets.disconnect")}</Button>
      </>}
    </div>}
    {exports.error ? <ErrorState error={exports.error} action={<Button variant="secondary" onClick={() => { void exports.refetch(); }}>{t("common.retry")}</Button>} /> : null}
    {connected && exports.data?.length ? <ul className="space-y-3 border-t border-platforma-border pt-3">
      {exports.data.map(item => <li key={item.id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
        <div className="min-w-0">
          {item.spreadsheet_id ? <a href={`https://docs.google.com/spreadsheets/d/${encodeURIComponent(item.spreadsheet_id)}/edit`} target="_blank" rel="noopener noreferrer" className="text-brand-700 underline">{t("googleSheets.open")}</a> : <span>{t("googleSheets.creationPending")}</span>}
          <p className="text-platforma-muted">{t(item.status === "succeeded" ? "googleSheets.exportedRows" : "googleSheets.transferPending", { count: item.row_count })}</p>
        </div>
        <Button id={`google-export-${item.id}`} data-focus-return-id={`google-export-${item.id}`} size="sm" variant="secondary" disabled={busy} onClick={() => startExport(item)}>{t(item.status === "succeeded" ? "googleSheets.refresh" : "common.retry")}</Button>
      </li>)}
    </ul> : null}
    <Modal open={dialog === "import"} title={t("googleSheets.import")} size="xl" focusReturnId={`google-import-${businessId}`} onClose={() => { if (!snapshot.isPending) setDialog(null); }}>
      <div className="space-y-4">
        <p className="break-words font-medium">{selected?.title}</p>
        {job && user ? <ImportJobReview key={job.id} job={job} userId={user.id} canCreate={canCreate} onChange={setJob} onImported={setJob} /> : <>
          <label className="block space-y-1 text-sm"><span>{t("googleSheets.sheet")}</span><Select aria-label={t("googleSheets.sheet")} value={sheetId} disabled={snapshot.isPending}
            options={(selected?.sheets ?? []).map(sheet => ({ value: String(sheet.sheetId), label: sheet.title }))}
            onChange={event => { setSheetId(event.target.value); setRequestKey(crypto.randomUUID()); snapshot.reset(); }} /></label>
          <p className="text-sm text-platforma-muted">{t("googleSheets.importLimit")}</p>
          {snapshot.error && <ErrorState error={snapshot.error} />}
          <Button disabled={!sheetId || !selected?.sheets.length} isLoading={snapshot.isPending} onClick={() => snapshot.mutate()}>{t("integrations.import.preview")}</Button>
        </>}
        {job?.status === "imported" && <p role="status">{t("googleSheets.imported", { count: job.imported_count })}</p>}
      </div>
    </Modal>
    <Modal open={dialog === "export"} title={t(target ? "googleSheets.refresh" : "googleSheets.export")} focusReturnId={`google-export-${target?.id ?? businessId}`} onClose={() => { if (!exportMutation.isPending) setDialog(null); }}>
      <div className="space-y-4">
        <p className="break-words">{t(target ? "googleSheets.refreshConfirm" : "googleSheets.exportConfirm", { email: connection.data?.email ?? "" })}</p>
        <p className="text-sm text-platforma-muted">{t("googleSheets.exportLimit")}</p>
        {exportMutation.error && <ErrorState error={exportMutation.error} />}
        <Button isLoading={exportMutation.isPending} onClick={() => exportMutation.mutate()}>{t(target ? "googleSheets.refresh" : "googleSheets.export")}</Button>
      </div>
    </Modal>
    <Modal open={dialog === "disconnect"} title={t("googleSheets.disconnect")} focusReturnId={`google-connection-${businessId}`} onClose={() => { if (!disconnect.isPending) setDialog(null); }}>
      <div className="space-y-4"><p>{t("googleSheets.disconnectConfirm")}</p>
        {connection.data?.retention_enabled && <p>{t("googleSheets.retentionNotice")}</p>}
        {disconnect.error && <ErrorState error={disconnect.error} />}
        <Button variant="danger" isLoading={disconnect.isPending} onClick={() => disconnect.mutate()}>{t("googleSheets.disconnect")}</Button>
      </div>
    </Modal>
  </section>;
}

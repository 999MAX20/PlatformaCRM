import { ImportErrorNotice } from "./ImportErrorNotice";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { importWorkspaceApi, type ImportWorkspace } from "../../api/importWorkspace";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { Modal } from "../../components/ui/Modal";
import { LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { useAuth } from "../auth/AuthProvider";

export function ImportProfiles({ workspace, sourceId, disabled, run }: {
  workspace: ImportWorkspace; sourceId: number; disabled: boolean;
  run: (operation: () => Promise<ImportWorkspace>) => Promise<ImportWorkspace | undefined>;
}) {
  const { user } = useAuth();
  const { t } = useI18n(); const label = (key: string) => t(`importWorkspace.${key}`);
  const [name, setName] = useState(""); const [selected, setSelected] = useState("");
  const profiles = useQuery({ queryKey: ["import-profiles", workspace.business, user?.id, workspace.id, workspace.version], queryFn: () => importWorkspaceApi.profiles(workspace.id) });
  return <section className="space-y-3 border-b border-platforma-border pb-4" aria-label={label("profiles")}>
    {profiles.error && <ImportErrorNotice error={profiles.error} action={<Button onClick={() => void profiles.refetch()}>{label("reload")}</Button>} />}
    <div className="flex flex-wrap items-end gap-2">
      <Select label={label("profiles")} value={selected} disabled={disabled || profiles.isLoading} options={[{ value: "", label: label("chooseProfile") }, ...(!profiles.error ? profiles.data?.results || [] : []).map(item => ({ value: String(item.id), label: `${item.name} · ${label(item.entity_type)}` }))]} onChange={event => setSelected(event.target.value)} />
      <Button variant="secondary" disabled={disabled || !!profiles.error || !selected} onClick={() => void run(() => importWorkspaceApi.applyProfile(workspace.id, workspace.version, sourceId, Number(selected)))}>{label("applyProfile")}</Button>
      <Input label={label("profileName")} value={name} maxLength={128} disabled={disabled} onChange={event => setName(event.target.value)} />
      <Button variant="secondary" disabled={disabled || !name.trim()} onClick={async () => { if (await run(() => importWorkspaceApi.saveProfile(workspace.id, workspace.version, sourceId, name.trim()))) setName(""); }}>{label("saveProfile")}</Button>
    </div>
  </section>;
}

export function ImportActivationAction({ workspace, timezone, onBusy }: { workspace: ImportWorkspace; timezone: string; onBusy: (busy: boolean) => void }) {
  const { user } = useAuth();
  const { t, language } = useI18n(); const label = (key: string) => t(`importWorkspace.${key}`);
  const [open, setOpen] = useState(false); const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null); const [selected, setSelected] = useState<number[]>([]);
  const [completed, setCompleted] = useState(false);
  const preview = useQuery({ queryKey: ["import-activation", workspace.business, user?.id, workspace.id], queryFn: () => importWorkspaceApi.activation(workspace.id), enabled: open, staleTime: 0, refetchOnWindowFocus: false });
  const refresh = async () => { setSelected([]); setError(null); await preview.refetch(); };
  const activate = async () => {
    if (!preview.data || preview.error || busy || !selected.length) return;
    setBusy(true); onBusy(true); setError(null);
    try { await importWorkspaceApi.activate(workspace.id, preview.data.token, selected); setSelected([]); setCompleted(true); await preview.refetch(); }
    catch (failure) { setError(failure); }
    finally { setBusy(false); onBusy(false); }
  };
  return <>
    <Button variant="secondary" onClick={() => { setSelected([]); setCompleted(false); setError(null); setOpen(true); }}>{label("activateReview")}</Button>
    <Modal open={open} title={label("activateReview")} onClose={() => { if (!busy) setOpen(false); }}>
      <div className="space-y-4">
        <p className="text-sm">{label("activateHint")}</p>
        {(error || preview.error) && <ImportErrorNotice error={error || preview.error} action={<Button disabled={busy} onClick={() => void refresh()}>{label("reload")}</Button>} />}
        {preview.isFetching ? <LoadingState /> : <div className="max-h-80 space-y-2 overflow-auto">
          {(!preview.error ? preview.data?.records : [])?.map(record => <label key={record.id} className="flex items-start gap-3 rounded-control border border-platforma-border p-3 text-sm">
            <input type="checkbox" disabled={busy} checked={selected.includes(record.id)} onChange={event => setSelected(event.target.checked ? [...selected, record.id] : selected.filter(id => id !== record.id))} />
            <span>{new Intl.DateTimeFormat(language, { dateStyle: "medium", timeStyle: "short", timeZone: timezone }).format(new Date(record.start_at))}<br />{record.client_name} · {record.service_name} · {record.specialist_name}</span>
          </label>)}
          {!preview.error && preview.data?.records.length === 0 && <p className="text-sm text-platforma-muted">{label("activateEmpty")}</p>}
        </div>}
        {completed && <p role="status" className="text-sm">{label("activated")}</p>}
        <div className="flex justify-end gap-2"><Button variant="secondary" disabled={busy} onClick={() => setOpen(false)}>{label("close")}</Button><Button disabled={busy || preview.isFetching || !!preview.error || !selected.length} onClick={() => void activate()}>{label("activateConfirm")}</Button></div>
      </div>
    </Modal>
  </>;
}

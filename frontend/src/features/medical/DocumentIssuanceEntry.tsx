import { useEffect, useRef, useState } from "react";
import axios from "axios";
import { medicalIssuanceApi as api, type DocumentGrant, type GrantResult, type IssuanceScope, type IssuanceWorkspace } from "../../api/medicalIssuance";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { Textarea } from "../../components/ui/Textarea";
import { Modal } from "../../components/ui/Modal";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { useUnsavedEntryWarning } from "../auth/useUnsavedEntryWarning";
import { medicalRoleDenied } from "./roles/useMedicalRolePage";

const allowOpen = async () => true;
const ignoreOpen = () => {};
export function DocumentIssuanceEntry({ businessId, clientId, branchId, beforeOpen = allowOpen, onOpenChange = ignoreOpen }: {
  businessId: number; clientId: number; branchId: number; beforeOpen?: () => Promise<boolean>; onOpenChange?: (open: boolean) => void;
}) {
  const { t } = useI18n();
  const [context, setContext] = useState<{ scope: IssuanceScope; workspace: IssuanceWorkspace } | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [open, setOpen] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController(); setContext(null); setError(null);
    void (async () => {
      try {
        const workspace = await api.byClient({ client_id: clientId, business_id: businessId, branch_id: branchId }, controller.signal);
        const scope = { business_id: businessId, branch_id: branchId, patient_id: workspace.patient_id };
        if (!controller.signal.aborted) setContext({ scope, workspace });
      } catch (cause) { if (!controller.signal.aborted && !medicalRoleDenied(cause) && !(axios.isAxiosError(cause) && cause.response?.status === 404)) setError(cause); }
    })();
    return () => controller.abort();
  }, [businessId, clientId, branchId, attempt]);
  useEffect(() => () => onOpenChange(false), [onOpenChange]);
  if (error) return <ErrorState error={error} action={<Button onClick={() => setAttempt(n => n + 1)}>{t("common.retry")}</Button>} />;
  if (!context) return null;
  return <>
    <Button size="lg" variant="secondary" data-focus-return-id="medical-document-issuance" onClick={() => void (async () => {
      if (await beforeOpen()) { setOpen(true); onOpenChange(true); }
    })()}>{t("medical.issue.title")}</Button>
    {open ? <IssuanceDialog {...context} onClose={() => { setOpen(false); onOpenChange(false); setAttempt(n => n + 1); }} /> : null}
  </>;
}

function IssuanceDialog({ scope, workspace, onClose }: { scope: IssuanceScope; workspace: IssuanceWorkspace; onClose: () => void }) {
  const { t, language: locale } = useI18n();
  const [data, setData] = useState(workspace);
  const [encounter, setEncounter] = useState("");
  const [versions, setVersions] = useState<number[]>([]);
  const [representative, setRepresentative] = useState("");
  const [verified, setVerified] = useState(false);
  const [reason, setReason] = useState("");
  const [replaces, setReplaces] = useState<DocumentGrant | null>(null);
  const [revoke, setRevoke] = useState<DocumentGrant | null>(null);
  const [result, setResult] = useState<GrantResult | null>(null);
  const [pending, setPending] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [denied, setDenied] = useState(false);
  const [conflict, setConflict] = useState(false);
  const busy = useRef(false);
  const controller = useRef(new AbortController());
  const request = useRef<{ fingerprint: string; key: string } | null>(null);
  const dirty = Boolean(reason || verified || versions.length || replaces || revoke || result?.code);
  useUnsavedEntryWarning(dirty);
  useEffect(() => { const active = new AbortController(); controller.current = active; return () => active.abort(); }, []);
  const close = () => { if (!busy.current && (!dirty || window.confirm(t("medical.issue.closeConfirm")))) onClose(); };
  function fail(cause: unknown) {
    if (controller.current.signal.aborted) return;
    setError(cause);
    if (medicalRoleDenied(cause)) { setDenied(true); setResult(null); setVersions([]); setReason(""); }
    else if (axios.isAxiosError(cause) && cause.response?.status === 409) setConflict(true);
  }
  async function load(id = encounter, before?: number, kind: "encounters" | "versions" | "grants" = "encounters") {
    setLoading(true); setError(null);
    try {
      const next = await api.workspace({ ...scope, ...(id ? { encounter_id: Number(id) } : {}), ...(before ? { [kind === "encounters" ? "before_id" : kind === "versions" ? "before_version_id" : "before_grant_id"]: before } : {}) }, controller.current.signal);
      if (!controller.current.signal.aborted) { setData(old => before ? { ...old, [kind]: [...old[kind], ...next[kind]],
        [kind === "encounters" ? "next_before_id" : kind === "versions" ? "next_before_version_id" : "next_before_grant_id"]: kind === "encounters" ? next.next_before_id : kind === "versions" ? next.next_before_version_id : next.next_before_grant_id } : next); setConflict(false); }
    } catch (cause) { fail(cause); }
    finally { if (!controller.current.signal.aborted) setLoading(false); }
  }
  async function command(kind: "create" | "activate" | "revoke", grant?: DocumentGrant) {
    if (busy.current || loading || denied || conflict) return;
    const payload = kind === "create" ? { ...scope, encounter_id: Number(encounter), version_ids: versions,
      personally_verified: verified, verification_reason: reason, ...(representative ? { representative_id: Number(representative) } : {}), ...(replaces ? { replaces_id: replaces.id } : {}) } :
      { ...scope, expected_revision: grant!.revision, action: kind, reason: kind === "revoke" ? reason : "" };
    const fingerprint = JSON.stringify([kind, grant?.id, payload]);
    if (request.current?.fingerprint !== fingerprint) request.current = { fingerprint, key: crypto.randomUUID() };
    busy.current = true; setPending(true); setError(null);
    try {
      const value = kind === "create" ? await api.create(payload as Parameters<typeof api.create>[0], request.current.key, controller.current.signal) :
        await api.transition(grant!.id, payload as Parameters<typeof api.transition>[1], request.current.key, controller.current.signal);
      if (!controller.current.signal.aborted) {
        setResult(value); setVersions([]); setVerified(false); setReason(""); setReplaces(null); setRevoke(null); request.current = null;
        await load();
      }
    } catch (cause) { fail(cause); }
    finally { busy.current = false; if (!controller.current.signal.aborted) setPending(false); }
  }
  const portal = `${window.location.origin}/medical-documents/${encodeURIComponent(data.business_slug)}`;
  return <Modal open title={t("medical.issue.title")} size="lg" onClose={close} closeOnBackdrop={false} focusReturnId="medical-document-issuance" testId="medical-document-issuance">
    {denied ? <ErrorState message={t("medical.denied")} /> : <div className="min-w-0 space-y-5">
      <p className="text-sm text-platforma-subtle">{t("medical.issue.synthetic")}</p>
      {result ? <section className="space-y-3 rounded-lg border border-platforma-border p-4" aria-label={t("medical.issue.saved")}>
        <p role="status" className="font-semibold">{t("medical.issue.saved")}</p>
        {result.code ? <><Input readOnly label={t("medical.issue.code")} value={result.code} autoComplete="off" /><p className="text-sm">{t("medical.issue.once")}</p></> : result.replayed ? <p>{t("medical.issue.replayed")}</p> : null}
        <Input readOnly label={t("medical.issue.link")} value={portal} />
        <p className="text-sm text-platforma-subtle">{t("medical.issue.notification")}</p>
        <Button variant="secondary" size="lg" onClick={() => setResult(null)}>{t("medical.issue.dismiss")}</Button>
      </section> : null}
      {!result && !revoke ? <form className="space-y-4" onSubmit={event => { event.preventDefault(); void command("create"); }}>
        <fieldset disabled={pending || loading || conflict} className="min-w-0 space-y-4">
          {replaces ? <p>{t("medical.issue.replacing", { id: replaces.id })}</p> : null}
          <Select label={t("medical.issue.encounter")} value={encounter} options={[{ value: "", label: t("medical.issue.selectEncounter") }, ...data.encounters.map(item => ({ value: item.id, label: `№${item.id} · ${new Date(item.started_at).toLocaleString(locale)}` }))]}
            onChange={event => { const next = event.target.value; setEncounter(next); setVersions([]); setReplaces(null); void load(next); }} />
          {data.next_before_id ? <Button type="button" variant="secondary" onClick={() => void load(encounter, data.next_before_id!)}>{t("medical.issue.moreEncounters")}</Button> : null}
          {encounter ? <fieldset className="space-y-2"><legend className="mb-2 text-sm font-medium">{t("medical.issue.documents")}</legend>
            {data.versions.length ? data.versions.map(item => <label key={item.id} className="flex min-h-11 items-start gap-3 rounded-lg border border-platforma-border p-3">
              <input type="checkbox" className="mt-1 h-5 w-5 shrink-0" checked={versions.includes(item.id)} onChange={event => setVersions(old => event.target.checked ? [...old, item.id] : old.filter(id => id !== item.id))} />
              <span className="min-w-0 break-words text-sm">{item.title}<span className="block text-platforma-subtle">{t("medical.issue.version", { revision: item.revision })} · {t(item.finalized ? "medical.issue.ready" : "medical.issue.waiting")}</span></span>
            </label>) : <p className="text-sm text-platforma-subtle">{t("medical.issue.empty")}</p>}
          </fieldset> : null}
          {data.next_before_version_id ? <Button type="button" variant="secondary" onClick={() => void load(encounter, data.next_before_version_id!, "versions")}>{t("medical.issue.moreDocuments")}</Button> : null}
          <Select label={t("medical.issue.recipient")} value={representative} options={[{ value: "", label: t("medical.issue.patient") }, ...data.representatives.map(item => ({ value: item.id, label: item.name }))]} onChange={event => { setRepresentative(event.target.value); setVerified(false); }} />
          <label className="flex min-h-11 items-center gap-3 text-sm"><input type="checkbox" className="h-5 w-5 shrink-0" checked={verified} onChange={event => setVerified(event.target.checked)} />{t("medical.issue.verified")}</label>
          <Textarea label={t("medical.issue.verification")} value={reason} required maxLength={2000} onChange={event => setReason(event.target.value)} />
        </fieldset>
        <Button type="submit" size="lg" isLoading={pending} disabled={loading || conflict || !verified || !reason.trim() || !versions.length || !encounter}>{t("medical.issue.create")}</Button>
      </form> : null}
      {revoke ? <form className="space-y-3" onSubmit={event => { event.preventDefault(); void command("revoke", revoke); }}>
        <p>{t("medical.issue.revokeConfirm", { id: revoke.id })}</p><Textarea label={t("medical.issue.reason")} required maxLength={2000} value={reason} disabled={pending} onChange={event => setReason(event.target.value)} />
        <div className="flex flex-wrap gap-2"><Button size="lg" type="submit" disabled={!reason.trim() || conflict} isLoading={pending}>{t("medical.issue.revoke")}</Button><Button size="lg" variant="secondary" disabled={pending} onClick={() => { setRevoke(null); setReason(""); }}>{t("common.cancel")}</Button></div>
      </form> : null}
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={conflict ? t("medical.clinical.conflict") : getApiErrorMessage(error)} action={<Button variant="secondary" disabled={pending} onClick={() => void load()}>{t("common.retry")}</Button>} /> : null}
      {!revoke && !replaces && !result ? <section className="space-y-3"><h3 className="font-semibold">{t("medical.issue.history")}</h3>
        {data.grants.length ? data.grants.map(grant => <div key={grant.id} className="space-y-2 border-t border-platforma-border pt-3" data-testid={`document-grant-${grant.id}`}>
          <p className="text-sm font-medium">№{grant.id} · {t(`medical.issue.state.${grant.state}`)}</p>
          {grant.expires_at ? <p className="text-sm text-platforma-subtle">{t("medical.issue.until", { date: new Date(grant.expires_at).toLocaleString(locale) })}</p> : null}
          <div className="flex flex-wrap gap-2">
            {grant.state === "pending" ? <Button size="lg" variant="secondary" disabled={pending || loading || conflict || dirty} onClick={() => void command("activate", grant)}>{t("medical.issue.activate")}</Button> : null}
            {grant.state !== "revoked" ? <Button size="lg" variant="secondary" disabled={pending || loading || conflict || dirty} onClick={() => { setRevoke(grant); setReason(""); }}>{t("medical.issue.revoke")}</Button> : null}
            <Button size="lg" variant="secondary" disabled={pending || loading || conflict || dirty} onClick={() => { setReplaces(grant); setEncounter(String(grant.encounter_id)); setVersions(grant.version_ids); setRepresentative(grant.representative_id ? String(grant.representative_id) : ""); setVerified(false); setReason(""); void load(String(grant.encounter_id)); }}>{t("medical.issue.reissue")}</Button>
          </div>
        </div>) : <p className="text-sm text-platforma-subtle">{t("medical.issue.noHistory")}</p>}
        {data.next_before_grant_id ? <Button size="lg" variant="secondary" disabled={pending || loading || dirty} onClick={() => void load(encounter, data.next_before_grant_id!, "grants")}>{t("medical.issue.moreHistory")}</Button> : null}
      </section> : null}
    </div>}
  </Modal>;
}

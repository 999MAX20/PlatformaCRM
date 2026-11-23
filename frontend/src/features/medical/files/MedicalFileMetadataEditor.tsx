import { useEffect, useRef, useState } from "react";
import axios from "axios";
import { medicalFilesApi as api, type MedicalFileScope, type MedicalFileVersion, type MedicalFileMetadata } from "../../../api/medicalFiles";
import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { Textarea } from "../../../components/ui/Textarea";
import { ErrorState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import { ClinicalPlanTeeth } from "../ClinicalPlanTeeth";
import type { MedicalFilesState } from "./MedicalFilesWorkspace";

export function MedicalFileMetadataEditor({ scope, file, onState, onSaved, onCancel, onDenied }: {
  scope: MedicalFileScope; file: MedicalFileVersion; onState: (state: MedicalFilesState) => void;
  onSaved: (version: MedicalFileVersion) => void; onCancel: () => void; onDenied: (cause: unknown) => void;
}) {
  const { t } = useI18n();
  const [base, setBase] = useState(file);
  const [description, setDescription] = useState(file.description);
  const [teeth, setTeeth] = useState(file.teeth);
  const [reason, setReason] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const attempt = useRef<{ key: string; payload: MedicalFileMetadata } | null>(null);
  const request = useRef<AbortController | null>(null);
  const dirty = description !== base.description || JSON.stringify(teeth) !== JSON.stringify(base.teeth) || Boolean(reason);
  useEffect(() => { onState({ dirty, pending }); }, [dirty, pending, onState]);
  useEffect(() => () => { request.current?.abort(); onState({ dirty: false, pending: false }); }, [onState]);
  const denied = (cause: unknown) => axios.isAxiosError(cause) && [401, 403, 404].includes(cause.response?.status ?? 0);
  async function save() {
    if (request.current || !reason.trim() || !base.actions?.edit_metadata) return;
    const controller = new AbortController(); request.current = controller; setPending(true); setError(null);
    attempt.current ??= { key: crypto.randomUUID(), payload: { ...scope, expected_revision: base.revision, description, teeth, reason } };
    try {
      const result = await api.updateMetadata(file.id, attempt.current.payload, attempt.current.key, controller.signal);
      const version = await api.version(scope, file.id, result.version_id, controller.signal);
      if (!controller.signal.aborted) onSaved(version);
    } catch (cause) {
      if (!controller.signal.aborted) {
        if (denied(cause)) onDenied(cause);
        else {
          if (axios.isAxiosError(cause) && [400, 409].includes(cause.response?.status ?? 0)) attempt.current = null;
          setError(cause);
        }
      }
    } finally { request.current = null; if (!controller.signal.aborted) setPending(false); }
  }
  async function reload() {
    if (request.current || (dirty && !window.confirm(t("medical.clinical.discard")))) return;
    const controller = new AbortController(); request.current = controller; setPending(true); setError(null);
    try {
      const latest = await api.version(scope, file.id, undefined, controller.signal);
      if (!controller.signal.aborted) {
        setBase(latest); setDescription(latest.description); setTeeth(latest.teeth); setReason(""); attempt.current = null;
      }
    } catch (cause) { if (!controller.signal.aborted) { if (denied(cause)) onDenied(cause); else setError(cause); } }
    finally { request.current = null; if (!controller.signal.aborted) setPending(false); }
  }
  return <form className="space-y-4" data-testid="medical-file-metadata" onSubmit={event => { event.preventDefault(); void save(); }}>
    <Textarea autoFocus label={t("medical.files.description")} value={description} maxLength={4000}
      disabled={pending || Boolean(attempt.current) || !base.actions?.edit_metadata} onChange={event => setDescription(event.target.value)} />
    <ClinicalPlanTeeth value={teeth} onChange={setTeeth} disabled={pending || Boolean(attempt.current) || !base.actions?.edit_metadata} readOnly={false} />
    <Textarea label={t("medical.reason")} value={reason} required maxLength={2000}
      disabled={pending || Boolean(attempt.current) || !base.actions?.edit_metadata} onChange={event => setReason(event.target.value)} />
    {error ? <ErrorState message={axios.isAxiosError(error) && error.response?.status === 409
      ? t("medical.clinical.conflict") : getApiErrorMessage(error)} /> : null}
    <div className="flex flex-wrap gap-2">
      <Button size="lg" type="submit" isLoading={pending} disabled={!reason.trim() || !base.actions?.edit_metadata}>{t(attempt.current ? "common.retry" : "common.save")}</Button>
      <Button size="lg" type="button" variant="secondary" disabled={pending} onClick={() => void reload()}>{t("medical.clinical.reload")}</Button>
      <Button size="lg" type="button" variant="secondary" disabled={pending} onClick={() => {
        if (!dirty || window.confirm(t("medical.clinical.discard"))) onCancel();
      }}>{t("common.cancel")}</Button>
    </div>
  </form>;
}

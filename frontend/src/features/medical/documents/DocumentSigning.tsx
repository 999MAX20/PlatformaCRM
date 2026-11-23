import { useCallback, useEffect, useState } from "react";
import { medicalSigningApi as api, type SigningState } from "../../../api/medicalSigning";
import type { DocumentReadScope } from "../../../api/medicalDocuments";
import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import { MedicalRoleCommand, type RoleFormControl } from "../roles/MedicalRoleCommand";
import { medicalRoleDenied } from "../roles/useMedicalRolePage";
import { SigningPdf } from "./SigningPdf";
import { formatDateTime } from "../../../lib/format";
import { localeByLanguage } from "../../calendar/calendarConstants";

export function DocumentSigning({ scope, versionId, control }: {
  scope: DocumentReadScope; versionId: number; control: RoleFormControl;
}) {
  const { t, language } = useI18n();
  const [value, setValue] = useState<SigningState | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  const reload = useCallback(() => { setValue(null); setAttempt(n => n + 1); }, []);
  useEffect(() => {
    const controller = new AbortController(); setValue(null); setError(null);
    api.read(scope, versionId, language, controller.signal).then(result => {
      if (!controller.signal.aborted) setValue(result);
    }).catch(cause => {
      if (!controller.signal.aborted) {
        if (medicalRoleDenied(cause)) control.onDenied(cause); else setError(cause);
      }
    });
    return () => controller.abort();
  }, [scope, versionId, language, attempt, control.onDenied]);
  const commandControl = { ...control, onSaved: reload };
  return <section className="min-w-0 space-y-3" data-testid="document-signing">
    <h4 className="text-sm font-medium">{t("medical.signing.title")}</h4>
    {error ? <ErrorState message={getApiErrorMessage(error)} action={<Button type="button" size="lg" onClick={reload}>{t("common.retry")}</Button>} /> : !value ? <LoadingState /> : <>
      <p className="text-sm text-platforma-subtle">{t(value.synthetic_enabled ? "medical.signing.synthetic" : "medical.signing.unavailable")}</p>
      {value.current ? <p role="status" className="text-sm font-medium">{t(`medical.signing.${value.current.state}`)}</p> : null}
      {value.finalization ? <div className="space-y-1 text-sm" data-testid="document-finalization">
        <p className="font-medium">{t("medical.signing.finalized")}</p>
        <p className="break-words text-platforma-subtle">{value.finalization.actor.name} · {formatDateTime(value.finalization.created_at, undefined, true, localeByLanguage[language])}</p>
      </div> : null}
      {value.next_signer ? <p className="text-sm">{t("medical.signing.next")}: {t(`medical.rules.role.${value.next_signer}`)}</p> : null}
      {!value.prerequisites.ready && !value.finalization ? <p className="text-sm">{t("medical.signing.reviewRequired")}</p> : null}
      {(value.finalization || value.synthetic_enabled && (value.current || value.artifact?.scan_status === "clean")) ? <SigningPdf
        key={value.finalization?.artifact_id ?? value.current?.artifact_id ?? value.artifact!.id} scope={scope} versionId={versionId}
        artifactId={value.finalization?.artifact_id ?? value.current?.artifact_id ?? value.artifact!.id} onDenied={control.onDenied} /> : null}
      {value.can_prepare && !value.artifact ? <MedicalRoleCommand payload={{ ...scope, language }} dirty={false} control={commandControl}
        label={t("medical.signing.prepare")} submit={data => api.prepare(versionId, data)}>{null}</MedicalRoleCommand> : null}
      {value.artifact && value.artifact.scan_status !== "clean" ? <p role="status" className="text-sm">{t("medical.signing.quarantine")}</p> : null}
      {value.can_start && value.artifact ? <MedicalRoleCommand payload={{ ...scope, artifact_id: value.artifact.id }} dirty={false} control={commandControl}
        label={t("medical.signing.start")} submit={(data, key) => api.start(versionId, data, key)}>{null}</MedicalRoleCommand> : null}
      {value.current && value.can_sign ? <MedicalRoleCommand payload={{ ...scope, session_id: value.current.id, expected_revision: value.current.revision, action: "sign" as const }}
        dirty={false} control={commandControl} label={t("medical.signing.sign")} submit={(data, key) => api.advance(versionId, data, key)}>{null}</MedicalRoleCommand> : null}
      {value.current && value.can_cancel ? <MedicalRoleCommand payload={{ ...scope, session_id: value.current.id, expected_revision: value.current.revision, action: "cancel" as const }}
        dirty={false} control={commandControl} label={t("medical.signing.cancel")} submit={(data, key) => api.advance(versionId, data, key)}>{null}</MedicalRoleCommand> : null}
      {value.can_finalize && value.finalize_artifact_id ? <MedicalRoleCommand
        payload={{ ...scope, artifact_id: value.finalize_artifact_id, expected_state_revision: value.state_revision }} dirty={false}
        control={{ ...control, onSaved: () => { reload(); control.onSaved(); } }} label={t("medical.signing.finalize")}
        submit={(data, key) => api.finalize(versionId, data, key)}>{null}</MedicalRoleCommand> : null}
      <Button type="button" size="lg" variant="secondary" onClick={reload}>{t("medical.signing.refresh")}</Button>
    </>}
  </section>;
}

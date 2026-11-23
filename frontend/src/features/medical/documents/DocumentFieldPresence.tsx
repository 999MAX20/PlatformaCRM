import { useEffect, useState } from "react";
import { medicalDocumentArtifactsApi as api, type DocumentArtifactScope, type DocumentFieldRequirements } from "../../../api/medicalDocumentArtifacts";
import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import { medicalRoleDenied } from "../roles/useMedicalRolePage";
import { documentFieldLabel } from "../templates/TemplateFields";

export function DocumentFieldPresence({ scope, versionId, onDenied }: {
  scope: DocumentArtifactScope; versionId: number; onDenied: (cause: unknown) => void;
}) {
  const { t } = useI18n();
  const [value, setValue] = useState<DocumentFieldRequirements | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController(); setValue(null); setError(null);
    api.requirements(scope, versionId, controller.signal).then(result => {
      if (!controller.signal.aborted) setValue(result);
    }).catch(cause => {
      if (!controller.signal.aborted) {
        if (medicalRoleDenied(cause)) onDenied(cause); else setError(cause);
      }
    });
    return () => controller.abort();
  }, [scope, versionId, attempt, onDenied]);
  return <section className="min-w-0 space-y-2" data-testid="document-field-presence">
    <h3 className="text-sm font-semibold">{t("medical.rules.fieldPresence")}</h3>
    {error ? <ErrorState message={getApiErrorMessage(error)} action={<Button type="button" size="lg" variant="secondary"
      onClick={() => setAttempt(previous => previous + 1)}>{t("common.retry")}</Button>} /> : !value ? <LoadingState /> : <>
      {!value.configured ? <p className="text-sm">{t("medical.rules.notCaptured")}</p> : !value.fields.length ?
        <p className="text-sm">{t("medical.rules.none")}</p> : <ul className="divide-y divide-platforma-border">
          {value.fields.map(item => <li key={item.field} className="flex flex-wrap justify-between gap-x-4 gap-y-1 py-2 text-sm">
            <span className="min-w-0 break-words">{documentFieldLabel(item.field, t)}</span>
            <span className="font-medium">{t(item.present ? "medical.rules.fieldPresent" : "medical.rules.fieldMissing")}</span>
          </li>)}
        </ul>}
    </>}
  </section>;
}

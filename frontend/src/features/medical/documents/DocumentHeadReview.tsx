import { useCallback, useEffect, useState } from "react";
import { medicalDocumentsApi as api, type DocumentReadScope, type DocumentHeadReview as HeadReview } from "../../../api/medicalDocuments";
import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import { formatDateTime } from "../../../lib/format";
import { localeByLanguage } from "../../calendar/calendarConstants";
import { MedicalRoleCommand, type RoleFormControl } from "../roles/MedicalRoleCommand";
import { medicalRoleDenied } from "../roles/useMedicalRolePage";

export function DocumentHeadReview({ scope, versionId, control }: {
  scope: DocumentReadScope; versionId: number; control: RoleFormControl;
}) {
  const { t, language } = useI18n();
  const [value, setValue] = useState<HeadReview | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  const reload = useCallback(() => { setValue(null); setAttempt(n => n + 1); }, []);
  useEffect(() => {
    const controller = new AbortController(); setValue(null); setError(null);
    api.headReview(scope, versionId, controller.signal).then(result => {
      if (!controller.signal.aborted) setValue(result);
    }).catch(cause => {
      if (!controller.signal.aborted) {
        if (medicalRoleDenied(cause)) control.onDenied(cause); else setError(cause);
      }
    });
    return () => controller.abort();
  }, [scope, versionId, attempt, control.onDenied]);
  return <section className="min-w-0 space-y-3" data-testid="document-head-review">
    {error ? <ErrorState message={getApiErrorMessage(error)} action={<Button type="button" size="lg" variant="secondary"
      onClick={reload}>{t("common.retry")}</Button>} /> : !value ? <LoadingState /> : value.required ? <>
      <p className="break-words text-sm font-medium">{t(value.confirmation ? "medical.documents.headConfirmed" : "medical.documents.headWaiting")}</p>
      {value.confirmation ? <p className="break-words text-sm text-platforma-subtle">{value.confirmation.actor.name} · {formatDateTime(value.confirmation.created_at, undefined, true, localeByLanguage[language])}</p> : null}
      {value.can_confirm && "head_branch_id" in scope ? <MedicalRoleCommand
        payload={{ ...scope, expected_state_revision: value.state_revision }} dirty={false}
        control={{ ...control, onSaved: () => { reload(); control.onSaved(); } }}
        label={t("medical.documents.headConfirm")} submit={(data, key) => api.headConfirm(versionId, data, key)}>
        {null}
      </MedicalRoleCommand> : null}
    </> : null}
  </section>;
}

import { useCallback, useEffect, useRef, useState } from "react";
import { medicalDocumentsApi as api, type DocumentReadScope, type DocumentReview as Review } from "../../../api/medicalDocuments";
import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { Textarea } from "../../../components/ui/Textarea";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import { formatDateTime } from "../../../lib/format";
import { localeByLanguage } from "../../calendar/calendarConstants";
import { MedicalRoleCommand, type RoleFormControl } from "../roles/MedicalRoleCommand";
import { medicalRoleDenied } from "../roles/useMedicalRolePage";
import { DocumentSigning } from "./DocumentSigning";
import { DocumentHeadReview } from "./DocumentHeadReview";

export function DocumentReview({ scope, versionId, control, canEdit, onState, headRequired }: {
  scope: DocumentReadScope; versionId: number; control: RoleFormControl; canEdit: boolean; onState: (state: string) => void;
  headRequired: boolean;
}) {
  const { t, language } = useI18n();
  const [review, setReview] = useState<Review | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [pending, setPending] = useState(false);
  const [open, setOpen] = useState(false);
  const request = useRef<AbortController | null>(null);
  const load = useCallback(async (before?: number) => {
    request.current?.abort(); const controller = new AbortController(); request.current = controller;
    setPending(true); setError(null);
    try {
      const page = await api.review(scope, versionId, before, controller.signal);
      if (!controller.signal.aborted) {
        setReview(previous => ({ ...page, results: before && previous ? [...previous.results, ...page.results] : page.results }));
        onState(page.document_state);
      }
    } catch (cause) {
      if (!controller.signal.aborted) {
        if (medicalRoleDenied(cause)) { setReview(null); control.onDenied(cause); }
        else setError(cause);
      }
    } finally { if (!controller.signal.aborted) setPending(false); }
  }, [scope, versionId, onState, control.onDenied]);
  useEffect(() => { void load(); return () => request.current?.abort(); }, [load]);
  return <section className="space-y-3" data-testid="document-review">
    {pending ? <LoadingState /> : null}
    {error ? <ErrorState error={error} message={getApiErrorMessage(error)} action={<Button type="button" size="lg" onClick={() => void load()}>{t("common.retry")}</Button>} /> : null}
    {review && canEdit && review.can_transition && !("head_branch_id" in scope) ?
      <ReviewForm key={`review-${review.state_revision}`} scope={scope} versionId={versionId} review={review}
        control={{ ...control, onSaved: () => { control.onSaved(); setReview(null); void load(); } }} /> : null}
    {headRequired && review && !error ? <DocumentHeadReview key={`head-${review.state_revision}`} scope={scope} versionId={versionId}
      control={{ ...control, onSaved: () => { control.onSaved(); void load(); } }} /> : null}
    {review && ["reviewed", "finalized"].includes(review.document_state) && !error ? <DocumentSigning key={`signing-${review.state_revision}`} scope={scope} versionId={versionId} control={{ ...control, onSaved: () => { control.onSaved(); void load(); } }} /> : null}
    <Button type="button" size="lg" variant="secondary" aria-expanded={open} onClick={() => setOpen(value => !value)}>{t("medical.documents.reviewHistory")}</Button>
    {open && review ? <div className="space-y-3">
      {!review.results.length && !pending && !error ? <p className="text-sm text-platforma-subtle">{t("medical.documents.reviewEmpty")}</p> : null}
      <ul className="divide-y divide-platforma-border">{review.results.map(event => <li key={event.id} className="space-y-1 py-3 text-sm">
        <p className="font-medium">{t(event.state === "draft" ? "medical.documents.reviewReturned" : event.state === "reviewed" ? "medical.documents.reviewConfirmed" : "medical.documents.reviewSubmitted")}</p>
        <p className="break-words text-platforma-subtle">{event.actor.name} · {formatDateTime(event.created_at, undefined, true, localeByLanguage[language])}</p>
        {event.reason ? <p className="whitespace-pre-wrap break-words">{event.reason}</p> : null}
        {event.head_confirmation ? <p className="break-words">{t("medical.documents.headConfirmed")} · {event.head_confirmation.actor.name} · {formatDateTime(event.head_confirmation.created_at, undefined, true, localeByLanguage[language])}</p> : null}
      </li>)}</ul>
      {review.next_before_id && !error ? <Button type="button" size="lg" variant="secondary" disabled={pending} onClick={() => void load(review.next_before_id!)}>{t("common.showMore")}</Button> : null}
    </div> : null}
  </section>;
}

function ReviewForm({ scope, versionId, review, control }: {
  scope: Exclude<DocumentReadScope, { head_branch_id: number }>; versionId: number; review: Review; control: RoleFormControl;
}) {
  const { t } = useI18n();
  const [reason, setReason] = useState("");
  const [returnSelected, setReturnSelected] = useState(false);
  const returning = review.document_state === "reviewed" || returnSelected;
  const target = returning ? "draft" as const : review.document_state === "ready_for_review" ? "reviewed" as const : "ready_for_review" as const;
  const payload = returning && !reason.trim() ? null : { ...scope, expected_state_revision: review.state_revision, target, reason };
  return <MedicalRoleCommand payload={payload} dirty={!!reason} control={control}
    label={t(returning ? "medical.documents.returnDraft" : target === "reviewed" ? "medical.documents.confirmReview" : "medical.documents.submitReview")}
    submit={(data, key) => api.transition(versionId, data, key)}>
    {review.document_state === "ready_for_review" ? <Button type="button" size="lg" variant="secondary" onClick={() => { setReturnSelected(value => !value); setReason(""); }}>
      {t(returnSelected ? "common.cancel" : "medical.documents.returnDraft")}
    </Button> : null}
    {returning ? <Textarea label={t("medical.documents.returnReason")} value={reason} maxLength={2000} rows={2}
      onChange={event => setReason(event.target.value)} /> : null}
  </MedicalRoleCommand>;
}

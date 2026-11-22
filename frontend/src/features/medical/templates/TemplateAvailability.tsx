import { useCallback, useEffect, useRef, useState } from "react";
import { medicalTemplatesApi as api, type TemplateAvailabilityHistory, type TemplateRow } from "../../../api/medicalTemplates";
import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { Textarea } from "../../../components/ui/Textarea";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import { MedicalRoleCommand, type RoleFormControl } from "../roles/MedicalRoleCommand";
import { medicalRoleDenied } from "../roles/useMedicalRolePage";

export function TemplateAvailabilityDetail({ businessId, row, control }: {
  businessId: number; row: TemplateRow; control: RoleFormControl;
}) {
  const { t, language } = useI18n();
  const [history, setHistory] = useState<TemplateAvailabilityHistory | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [reason, setReason] = useState("");
  const request = useRef<AbortController | null>(null);
  const load = useCallback(async (before?: number) => {
    request.current?.abort(); const controller = new AbortController(); request.current = controller;
    setLoading(true); setError(null);
    try {
      const page = await api.availability(businessId, row.template_id, before, controller.signal);
      if (!controller.signal.aborted) setHistory(previous => before && previous
        ? { ...previous, results: [...previous.results, ...page.results], next_before_revision: page.next_before_revision }
        : page);
    } catch (cause) {
      if (!controller.signal.aborted) { if (medicalRoleDenied(cause)) control.onDenied(cause); else setError(cause); }
    } finally { if (!controller.signal.aborted) setLoading(false); }
  }, [businessId, row.template_id, control.onDenied]);
  useEffect(() => { void load(); return () => request.current?.abort(); }, [load]);
  if (!history) return error
    ? <ErrorState message={getApiErrorMessage(error)} action={<Button onClick={() => void load()}>{t("common.retry")}</Button>} />
    : <LoadingState />;
  const label = t(history.is_active ? "medical.templates.pause" : "medical.templates.resume");
  return <div className="space-y-4">
    <h2 className="break-words text-base font-semibold">{row.title}</h2>
    <p role="status" className="text-sm">{t(history.is_active ? "medical.templates.active" : "medical.templates.inactive")}</p>
    <MedicalRoleCommand dirty={!!reason} control={control} label={label}
      payload={reason.trim() && !loading ? { business_id: businessId, is_active: !history.is_active,
        expected_revision: history.revision, reason } : null}
      submit={(payload, key) => api.setAvailability(row.template_id, payload, key)}>
      <Textarea label={t("medical.templates.availabilityReason")} value={reason} rows={3} maxLength={2000}
        required onChange={event => setReason(event.target.value)} />
    </MedicalRoleCommand>
    <section className="space-y-3" aria-label={t("medical.templates.availabilityHistory")}>
      <h3 className="text-base font-semibold">{t("medical.templates.availabilityHistory")}</h3>
      <ul className="divide-y divide-platforma-border">{history.results.map(change => <li key={change.id} className="space-y-1 py-3 text-sm">
        <p>{t(change.is_active ? "medical.templates.active" : "medical.templates.inactive")}</p>
        <p className="text-platforma-subtle">{new Intl.DateTimeFormat(language, { dateStyle: "medium", timeStyle: "short" }).format(new Date(change.created_at))}</p>
        <p className="whitespace-pre-wrap break-words">{change.reason}</p>
      </li>)}</ul>
      {!history.results.length ? <p className="text-sm text-platforma-subtle">{t("medical.templates.availabilityEmpty")}</p> : null}
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={getApiErrorMessage(error)} action={<Button disabled={control.guard.current.pending} onClick={() => void load(history.next_before_revision ?? undefined)}>{t("common.retry")}</Button>} /> : null}
      {history.next_before_revision && !error ? <Button variant="secondary" disabled={loading || control.guard.current.pending}
        onClick={() => void load(history.next_before_revision!)}>{t("medical.templates.more")}</Button> : null}
    </section>
  </div>;
}

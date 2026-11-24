import { useEffect, useState } from "react";
import { medicalOrdersApi, type OrderPreview, type OrderScope } from "../../../api/medicalOrders";
import { medicalTemplatesApi, type TemplateRow, type TemplateSearch as Filters } from "../../../api/medicalTemplates";
import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { Textarea } from "../../../components/ui/Textarea";
import { Modal } from "../../../components/ui/Modal";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import { medicalRoleDenied } from "../roles/useMedicalRolePage";
import { TemplateSearch } from "../templates/TemplateSearch";

export function OrderTemplatePicker({ scope, orderId, onApply, onSuggest, onClose, onDenied }: {
  scope: OrderScope; orderId?: number; onApply: (preview: OrderPreview) => void;
  onClose: () => void; onDenied: (cause: unknown) => void;
  onSuggest?: (preview: OrderPreview) => void;
}) {
  const { t } = useI18n();
  const [filters, setFilters] = useState<Filters>({});
  const [rows, setRows] = useState<TemplateRow[]>([]);
  const [before, setBefore] = useState<number>();
  const [cursor, setCursor] = useState<number | null>(null);
  const [choice, setChoice] = useState<number | null>(null);
  const [preview, setPreview] = useState<OrderPreview | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError(null); setPreview(null);
    (async () => {
      if (choice) {
        const value = await medicalOrdersApi.preview(scope, choice, orderId, controller.signal);
        if (!controller.signal.aborted) setPreview(value);
      } else {
        const page = await medicalTemplatesApi.approved(scope.business_id, before, controller.signal, filters);
        if (!controller.signal.aborted) { setRows(previous => before ? [...previous, ...page.results] : page.results); setCursor(page.next_before_id); }
      }
    })().catch(cause => { if (!controller.signal.aborted) {
      if (medicalRoleDenied(cause)) onDenied(cause); else setError(cause);
    } }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [scope, orderId, choice, before, filters, attempt, onDenied]);
  return <Modal open title={t("medical.documents.chooseTemplate")} size="lg" onClose={onClose}
    closeOnBackdrop={false} focusReturnId="order-template-open" testId="order-template-picker">
    <div className="space-y-4">
      {!choice ? <TemplateSearch approved disabled={loading} value={filters} onApply={value => {
        setRows([]); setCursor(null); setBefore(undefined); setFilters(value);
      }} /> : <Button size="lg" variant="secondary" onClick={() => { setChoice(null); setPreview(null); }}>{t("medical.documents.changeTemplate")}</Button>}
      {loading ? <LoadingState /> : error ? <ErrorState message={getApiErrorMessage(error)} action={
        <Button size="lg" onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button>} /> : preview ? <>
        <p className="break-words">{preview.template_source.template.title} · {t("medical.templates.version", { revision: preview.template_source.approval.revision })}</p>
        {preview.missing_fields.length ? <p role="status">{t("medical.documents.missingFields", { count: preview.missing_fields.length })}</p> : null}
        {preview.unknown_fields.length ? <p role="status">{t("medical.documents.unknownFields", { count: preview.unknown_fields.length })}</p> : null}
        <Textarea label={t("medical.orders.text")} value={preview.document_text} readOnly rows={8} />
        <Button size="lg" onClick={() => onApply(preview)}>{t("medical.orders.applyTemplate")}</Button>
        {onSuggest ? <Button size="lg" variant="secondary" disabled={Boolean(preview.missing_fields.length || preview.unknown_fields.length)} onClick={() => onSuggest(preview)}>{t("medical.assistance.useCompletion")}</Button> : null}
      </> : <>
        {!rows.length ? <p role="status">{t("medical.templates.noMatches")}</p> : null}
        <ul className="divide-y divide-platforma-border">{rows.map(row => <li className="py-2" key={row.template_id}>
          <Button size="lg" variant="secondary" className="h-auto w-full whitespace-normal text-left" onClick={() => setChoice(row.version_id)}>
            <span className="min-w-0 break-words">{row.title} · {t("medical.templates.version", { revision: row.revision })}</span>
          </Button>
        </li>)}</ul>
        {cursor ? <Button size="lg" variant="secondary" onClick={() => setBefore(cursor)}>{t("medical.templates.more")}</Button> : null}
      </>}
    </div>
  </Modal>;
}

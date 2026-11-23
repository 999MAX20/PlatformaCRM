import type { CapturedDocumentRules } from "../../../api/medicalDocumentRules";
import { useI18n } from "../../../lib/i18n";
import { DocumentRequirementsSummary } from "../templates/DocumentRequirementsSummary";

export function DocumentSavedRules({ rules }: { rules?: CapturedDocumentRules | null }) {
  const { t } = useI18n();
  return <details className="min-w-0 border-y border-platforma-border py-2" data-testid="document-saved-rules">
    <summary className="platforma-focus-ring min-h-11 cursor-pointer break-words py-2 text-sm font-semibold">{t("medical.rules.captured")}</summary>
    {rules ? <div className="space-y-3 py-2">
      <p className="break-words font-medium">{rules.name} · {t("medical.templates.version", { revision: rules.revision })}</p>
      <p className="text-sm text-platforma-subtle">{t("medical.rules.synthetic")}</p>
      <DocumentRequirementsSummary value={rules.rule} />
      <p className="text-sm">{t(rules.docx_allowed ? "medical.rules.docxEnabled" : "medical.rules.docxDisabled")}</p>
    </div> : <p className="py-2 text-sm text-platforma-subtle">{t("medical.rules.notCaptured")}</p>}
  </details>;
}

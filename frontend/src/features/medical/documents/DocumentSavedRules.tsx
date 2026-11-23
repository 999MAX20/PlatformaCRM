import type { CapturedDocumentRules } from "../../../api/medicalDocumentRules";
import { useState } from "react";
import type { DocumentArtifactScope } from "../../../api/medicalDocumentArtifacts";
import { DocumentFieldPresence } from "./DocumentFieldPresence";
import { useI18n } from "../../../lib/i18n";
import { DocumentRequirementsSummary } from "../templates/DocumentRequirementsSummary";

export function DocumentSavedRules({ rules, scope, versionId, onDenied }: { rules?: CapturedDocumentRules | null;
  scope: DocumentArtifactScope; versionId: number; onDenied: (cause: unknown) => void }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  return <details className="min-w-0 border-y border-platforma-border py-2" data-testid="document-saved-rules"
    onToggle={event => setOpen(event.currentTarget.open)}>
    <summary className="platforma-focus-ring min-h-11 cursor-pointer break-words py-2 text-sm font-semibold">{t("medical.rules.captured")}</summary>
    {rules ? <div className="space-y-3 py-2">
      <p className="break-words font-medium">{rules.name} · {t("medical.templates.version", { revision: rules.revision })}</p>
      <p className="text-sm text-platforma-subtle">{t("medical.rules.synthetic")}</p>
      <DocumentRequirementsSummary value={rules.rule} />
      {open ? <DocumentFieldPresence scope={scope} versionId={versionId} onDenied={onDenied} /> : null}
      <p className="text-sm">{t(rules.docx_allowed ? "medical.rules.docxEnabled" : "medical.rules.docxDisabled")}</p>
    </div> : <p className="py-2 text-sm text-platforma-subtle">{t("medical.rules.notCaptured")}</p>}
  </details>;
}

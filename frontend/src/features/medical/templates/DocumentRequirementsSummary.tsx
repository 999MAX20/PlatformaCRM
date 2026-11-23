import type { DocumentRequirements } from "../../../api/medicalDocumentRules";
import { useI18n } from "../../../lib/i18n";
import { documentFieldLabel } from "./TemplateFields";

export function DocumentRequirementsSummary({ value }: { value: DocumentRequirements }) {
  const { t } = useI18n();
  return <dl className="space-y-2 break-words text-sm">
    <div><dt className="font-medium">{t("medical.rules.moment")}</dt><dd>{t(`medical.rules.moment.${value.required_at}`)}</dd></div>
    <div><dt className="font-medium">{t("medical.rules.fields")}</dt><dd>{value.required_fields.map(field => documentFieldLabel(field, t)).join(", ") || t("medical.rules.none")}</dd></div>
    <div><dt className="font-medium">{t("medical.rules.reviewers")}</dt><dd>{value.reviewers.map(item => t(`medical.rules.role.${item}`)).join(", ")}</dd></div>
    <div><dt className="font-medium">{t("medical.rules.signers")}</dt><dd>{value.signers.map((item, index) => `${index + 1}. ${t(`medical.rules.role.${item}`)}`).join("; ") || t("medical.rules.noSigners")}</dd></div>
    <div><dt className="font-medium">{t("medical.rules.issuable")}</dt><dd>{t(value.issuable ? "medical.rules.issuanceAllowed" : "medical.rules.issuanceDenied")}</dd></div>
  </dl>;
}

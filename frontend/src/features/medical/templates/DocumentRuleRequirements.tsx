import { useState } from "react";
import type { DocumentRequirements, DocumentRuleAccess, RuleMoment, RuleSigner } from "../../../api/medicalDocumentRules";
import { Button } from "../../../components/ui/Button";
import { Select } from "../../../components/ui/Select";
import { useI18n } from "../../../lib/i18n";
import { documentFieldLabel } from "./TemplateFields";

export function DocumentRuleRequirements({ value, access, onChange }: {
  value: DocumentRequirements; access: DocumentRuleAccess; onChange: (value: DocumentRequirements) => void;
}) {
  const { t } = useI18n();
  const [field, setField] = useState("");
  const [signer, setSigner] = useState<RuleSigner | "">("");
  const available = access.fields.filter(item => !value.required_fields.includes(item));
  return <div className="min-w-0 space-y-4">
    <Select label={t("medical.rules.moment")} value={value.required_at}
      options={access.moments.map(item => ({ value: item, label: t(`medical.rules.moment.${item}`) }))}
      onChange={event => onChange({ ...value, required_at: event.target.value as RuleMoment })} />
    <label className="flex min-h-11 items-center gap-3 text-sm"><input type="checkbox" className="h-5 w-5 shrink-0 accent-brand-600"
      checked={value.issuable} onChange={event => onChange({ ...value, issuable: event.target.checked })} />{t("medical.rules.issuable")}</label>
    <fieldset className="space-y-2"><legend className="text-sm font-semibold">{t("medical.rules.fields")}</legend>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end"><div className="min-w-0 flex-1">
        <Select label={t("medical.fields.choose")} value={field} options={[{ value: "", label: t("common.select") },
          ...available.flatMap(item => { const label = documentFieldLabel(item, t); return label ? [{ value: item, label }] : []; })]}
          onChange={event => setField(event.target.value)} /></div>
        <Button type="button" size="lg" variant="secondary" disabled={!field || !available.includes(field)} onClick={() => {
          onChange({ ...value, required_fields: [...value.required_fields, field] }); setField("");
        }}>{t("medical.rules.addField")}</Button></div>
      <ul className="space-y-2">{value.required_fields.map(item => <li key={item} className="flex items-center justify-between gap-3">
        <span className="min-w-0 break-words text-sm">{documentFieldLabel(item, t)}</span>
        <Button type="button" size="lg" variant="secondary" aria-label={`${t("medical.templates.removeService")}: ${documentFieldLabel(item, t)}`}
          onClick={() => onChange({ ...value, required_fields: value.required_fields.filter(entry => entry !== item) })}>{t("medical.templates.removeService")}</Button>
      </li>)}</ul>
    </fieldset>
    <fieldset className="space-y-2"><legend className="text-sm font-semibold">{t("medical.rules.reviewers")}</legend>
      <p className="text-sm">{t("medical.rules.role.primary_clinician")}</p>
      <label className="flex min-h-11 items-center gap-3 text-sm"><input type="checkbox" className="h-5 w-5 shrink-0 accent-brand-600"
        checked={value.reviewers.includes("medical_head")} onChange={event => onChange({ ...value,
          reviewers: event.target.checked ? ["primary_clinician", "medical_head"] : ["primary_clinician"] })} />{t("medical.rules.role.medical_head")}</label>
    </fieldset>
    <fieldset className="space-y-2"><legend className="text-sm font-semibold">{t("medical.rules.signers")}</legend>
      <ol className="space-y-2">{value.signers.map((item, index) => <li key={item} className="flex flex-wrap items-center justify-between gap-2">
        <span className="min-w-0 break-words text-sm">{index + 1}. {t(`medical.rules.role.${item}`)}</span>
        <div className="flex flex-wrap gap-2"><Button type="button" size="lg" variant="secondary" disabled={index === 0}
          aria-label={`${t("medical.rules.moveEarlier")}: ${t(`medical.rules.role.${item}`)}`} onClick={() => {
            const next = [...value.signers]; [next[index - 1], next[index]] = [next[index], next[index - 1]]; onChange({ ...value, signers: next });
          }}>{t("medical.rules.moveEarlier")}</Button>
          <Button type="button" size="lg" variant="secondary" aria-label={`${t("medical.templates.removeService")}: ${t(`medical.rules.role.${item}`)}`}
            onClick={() => onChange({ ...value, signers: value.signers.filter(entry => entry !== item) })}>{t("medical.templates.removeService")}</Button></div>
      </li>)}</ol>
      {!value.signers.length ? <p className="text-sm text-platforma-subtle">{t("medical.rules.noSigners")}</p> : null}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end"><div className="min-w-0 flex-1"><Select label={t("medical.rules.signer")}
        value={signer} options={[{ value: "", label: t("common.select") }, ...access.signers.filter(item => !value.signers.includes(item))
          .map(item => ({ value: item, label: t(`medical.rules.role.${item}`) }))]}
        onChange={event => setSigner(event.target.value as RuleSigner | "")} /></div>
        <Button type="button" size="lg" variant="secondary" disabled={!signer || value.signers.includes(signer)} onClick={() => {
          if (signer) { onChange({ ...value, signers: [...value.signers, signer] }); setSigner(""); }
        }}>{t("medical.rules.addSigner")}</Button></div>
    </fieldset>
  </div>;
}

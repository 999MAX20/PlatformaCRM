import type { ClinicalHistoryFilters as Filters, ClinicalHistoryOptions } from "../../api/medicalClinical";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { useI18n } from "../../lib/i18n";

export function ClinicalHistoryFilters({ value, options, loading, onChange, onApply, onReset }: {
  value: Filters; options: ClinicalHistoryOptions; loading: boolean; onChange: (value: Filters) => void;
  onApply: () => void; onReset: () => void;
}) {
  const { t } = useI18n();
  const all = { value: "", label: t("common.all") };
  return <form className="space-y-3" data-testid="clinical-history-filters" onSubmit={event => { event.preventDefault(); onApply(); }}>
    <div className="grid min-w-0 gap-3 sm:grid-cols-2">
      <Input type="date" label={t("timeline.dateFrom")} value={value.date_from ?? ""} disabled={loading}
        onChange={event => onChange({ ...value, date_from: event.target.value || undefined })} />
      <Input type="date" label={t("timeline.dateTo")} value={value.date_to ?? ""} disabled={loading}
        onChange={event => onChange({ ...value, date_to: event.target.value || undefined })} />
      <Select label={t("medical.branch")} value={value.branch_id ?? ""} disabled={loading}
        options={[all, ...options.branches.map(row => ({ value: row.id, label: row.name }))]}
        onChange={event => onChange({ ...value, branch_id: Number(event.target.value) || undefined })} />
      <Select label={t("medical.clinical.currentAuthor")} value={value.author_id ?? ""} disabled={loading}
        options={[all, ...options.authors.map(row => ({ value: row.id, label: row.name || t("medical.clinical.authorUnknown") }))]}
        onChange={event => onChange({ ...value, author_id: Number(event.target.value) || undefined })} />
      <Select label={t("appointment.status")} value={value.state ?? ""} disabled={loading}
        options={[all, ...(["draft", "finalized"] as const).map(state => ({ value: state, label: t(`medical.clinical.state.${state}`) }))]}
        onChange={event => onChange({ ...value, state: (event.target.value || undefined) as Filters["state"] })} />
    </div>
    <div className="flex flex-wrap gap-2">
      <Button type="submit" size="lg" disabled={loading}>{t("crmFilters.apply")}</Button>
      <Button type="button" size="lg" variant="secondary" disabled={loading} onClick={onReset}>{t("common.reset")}</Button>
    </div>
  </form>;
}

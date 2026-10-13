import { useI18n } from "../../lib/i18n";
import { Input } from "../ui/Input";
import { Select } from "../ui/Select";
import { DateRangePicker } from "../ui/DateRangePicker";
import type { CrmFilterKind, CrmFilterValues } from "./useCrmFilters";

export type FilterOption = { value: string | number; label: string };
export type FilterOptions = { source?: FilterOption[]; tag?: FilterOption[]; segment?: FilterOption[]; assignees?: FilterOption[]; stage?: FilterOption[] };
export function filterFields(kind: CrmFilterKind): string[] {
  return kind === "clients" ? ["source", "tag", "segment", "handoff", "created", "archive"]
    : kind === "leads" ? ["statuses", "assignees", "source", "created", "attention_reason", "archive"]
      : ["statuses", "stage", "assignees", "source", "amount", "created", "expected_close", "attention_reason", "archive"];
}
export function fieldOptions(kind: CrmFilterKind, key: string, supplied: FilterOptions, t: (key: string) => string): FilterOption[] {
  if (key === "statuses") return (kind === "leads" ? ["new", "contacted", "in_progress", "appointment_created", "closed", "lost"] : ["open", "won", "lost"]).map(value => ({ value, label: t(`crmFilters.status.${value}`) }));
  if (key === "attention_reason") return (kind === "leads" ? ["unassigned", "no_action", "overdue_action"] : ["sla", "no_action", "closing"]).map(value => ({ value, label: t(`crmFilters.reason.${value}`) }));
  if (key === "assignees") return [{ value: "unassigned", label: t("crmFilters.unassigned") }, ...(supplied.assignees || [])];
  return (supplied[key as keyof FilterOptions] || []).filter(option => String(option.value) !== "" && String(option.value) !== "all");
}

export function CrmFilterFields({ kind, value, onChange, options, today }: {
  kind: CrmFilterKind; value: CrmFilterValues; onChange: (patch: CrmFilterValues) => void; options: FilterOptions; today: string;
}) {
  const { t } = useI18n();
  return <div className="space-y-4">{filterFields(kind).map(key => {
    const label = t(`crmFilters.${key}`);
    if (["created", "expected_close"].includes(key)) return <DateRangePicker key={key} label={label} value={{ from: value[`${key}_from`], to: value[`${key}_to`] }} onChange={range => onChange({ [`${key}_from`]: range.from, [`${key}_to`]: range.to })} today={today} />;
    if (key === "amount") return <fieldset key={key} className="grid grid-cols-2 gap-2"><legend className="mb-1.5 text-sm font-medium">{label}</legend><Input label={t("crmFilters.from")} type="number" min="0" step="any" value={value.amount_min} onChange={event => onChange({ amount_min: event.target.value })} /><Input label={t("crmFilters.to")} type="number" min="0" step="any" value={value.amount_max} onChange={event => onChange({ amount_max: event.target.value })} /></fieldset>;
    if (key === "archive") return <Select key={key} label={label} value={value.archive} onChange={event => onChange({ archive: event.target.value })} options={["active", "archived", "all"].map(item => ({ value: item, label: t(`crmFilters.archive.${item}`) }))} />;
    if (key === "handoff") return <label key={key} className="flex min-h-11 items-center gap-3 text-sm"><input type="checkbox" checked={value.handoff === "true"} onChange={event => onChange({ handoff: event.target.checked ? "true" : "" })} className="h-4 w-4 accent-brand-600" />{label}</label>;
    if (key === "segment") return <Select key={key} label={label} value={value.segment} onChange={event => onChange({ segment: event.target.value })} options={[{ value: "", label: t("common.all") }, ...(options.segment || []).filter(item => item.value !== "")]} />;
    const available = fieldOptions(kind, key, options, t);
    const selected = (value[key] || "").split(",").filter(Boolean);
    const selectedLabels = selected.map(item => available.find(option => String(option.value) === item)?.label || (item === "all" ? t("common.all") : item));
    return <fieldset key={key} className="min-w-0"><legend className="mb-1.5 text-sm font-medium text-platforma-text">{label}</legend>
      <details className="rounded-control border border-platforma-control bg-platforma-card">
        <summary className="platforma-focus-ring flex min-h-11 cursor-pointer list-inside items-center px-3 py-2 text-sm text-platforma-text">{selectedLabels.length ? selectedLabels.join(", ") : t("common.all")}</summary>
        <div className="max-h-52 overflow-y-auto border-t border-platforma-border p-2">
          <label className="flex min-h-11 items-center gap-3 rounded-control px-2 text-sm hover:bg-surface-hover"><input type="checkbox" className="h-4 w-4 accent-brand-600" checked={!selected.length || selected.includes("all")} onChange={() => onChange({ [key]: key === "statuses" ? "all" : "" })} />{t("common.all")}</label>
          {available.map(option => <label key={option.value} className="flex min-h-11 items-center gap-3 rounded-control px-2 text-sm hover:bg-surface-hover"><input type="checkbox" className="h-4 w-4 accent-brand-600" checked={selected.includes(String(option.value))} onChange={event => {
            const next = selected.filter(item => item !== "all" && item !== String(option.value));
            if (event.target.checked) next.push(String(option.value));
            onChange({ [key]: next.length ? next.join(",") : key === "statuses" ? "all" : "" });
          }} />{option.label}</label>)}
        </div>
      </details>
      {key === "tag" && selected.length > 1 ? <div className="mt-2"><Select aria-label={t("crmFilters.tagMode")} value={value.tag_mode} options={[{ value: "any", label: t("crmFilters.tagAny") }, { value: "all", label: t("crmFilters.tagAll") }]} onChange={event => onChange({ tag_mode: event.target.value })} /></div> : null}
    </fieldset>;
  })}</div>;
}

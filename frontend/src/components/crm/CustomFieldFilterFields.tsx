import type { CustomFieldDefinition } from "../../types";
import { useI18n } from "../../lib/i18n";
import { customFieldOptions } from "../../lib/customFields";
import { Input } from "../ui/Input";
import { Select } from "../ui/Select";
import type { CrmFilterValues } from "./useCrmFilters";

export function customFieldOperators(type?: string) {
  return ["equals", "is_empty", ...(["number", "money", "date"].includes(type || "") ? ["gte", "lte"] : []), ...(["text", "textarea", "email", "phone", "url"].includes(type || "") ? ["contains"] : [])];
}

export function validCustomFieldFilter(value: CrmFilterValues, definitions: CustomFieldDefinition[]) {
  if (!value.custom_field) return true;
  const selected = definitions.find(field => String(field.id) === value.custom_field && (field.options_json.display as { in_filters?: boolean } | undefined)?.in_filters);
  const operator = value.custom_operator || "equals";
  if (selected?.field_type === "multiselect" && operator !== "is_empty") {
    const options = customFieldOptions(selected);
    const values = selectedFilterOptions(value.custom_value);
    return operator === "equals" && values.length > 0 && values.every(item => options.some(option => option.value === item));
  }
  return !!selected && customFieldOperators(selected.field_type).includes(operator) && (operator === "is_empty" || !!value.custom_value?.trim());
}

function selectedFilterOptions(value?: string) {
  if (!value) return [];
  if (!value.startsWith("[")) return [value];
  try {
    const parsed: unknown = JSON.parse(value);
    return Array.isArray(parsed) && parsed.every(item => typeof item === "string") ? parsed as string[] : [];
  } catch {
    return [];
  }
}

export function CustomFieldFilterFields({ definitions, value, onChange, className = "space-y-3" }: {
  definitions: CustomFieldDefinition[];
  value: CrmFilterValues;
  onChange: (patch: CrmFilterValues) => void;
  className?: string;
}) {
  const { t } = useI18n();
  const label = (key: string) => t(`importWorkspace.${key}`);
  const available = definitions.filter(field => (field.options_json.display as { in_filters?: boolean } | undefined)?.in_filters);
  const selected = available.find(field => String(field.id) === value.custom_field);
  const selectedOptions = selectedFilterOptions(value.custom_value);
  if (!available.length && !value.custom_field) return null;
  return <fieldset className={className}>
    <Select label={label("customFilter")} value={value.custom_field || ""} options={[{ value: "", label: label("choose") }, ...available.map(field => ({ value: String(field.id), label: field.label }))]}
      onChange={event => onChange({ custom_field: event.target.value, custom_operator: "equals", custom_value: "" })} />
    {!!value.custom_field && <>
      <Select label={label("operator")} value={value.custom_operator || "equals"} options={customFieldOperators(selected?.field_type).map(operator => ({ value: operator, label: label(operator) }))} onChange={event => onChange({ custom_operator: event.target.value })} />
      {value.custom_operator !== "is_empty" && (selected?.field_type === "multiselect"
        ? <fieldset className="space-y-2">
          <legend className="mb-2 text-sm font-semibold text-platforma-subtle">{label("value")}</legend>
          {customFieldOptions(selected).map(option => <label key={option.value} className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={selectedOptions.includes(option.value)} onChange={event => onChange({ custom_value: JSON.stringify(event.target.checked ? [...selectedOptions, option.value] : selectedOptions.filter(item => item !== option.value)) })} />
            {option.label}
          </label>)}
        </fieldset>
        : selected?.field_type === "boolean"
        ? <Select label={label("value")} value={value.custom_value || ""} options={[{ value: "", label: label("choose") }, { value: "true", label: t("crmCard.yes") }, { value: "false", label: t("crmCard.no") }]} onChange={event => onChange({ custom_value: event.target.value })} />
        : <Input label={label("value")} type={selected?.field_type === "date" ? "date" : "text"} value={value.custom_value || ""} onChange={event => onChange({ custom_value: event.target.value })} />)}
    </>}
  </fieldset>;
}

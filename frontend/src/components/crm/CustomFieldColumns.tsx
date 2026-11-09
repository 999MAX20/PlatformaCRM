import { EntityExportButton } from "./EntityExportButton";
import { useEffect, useState } from "react";
import { ArrowDown, ArrowUp } from "lucide-react";
import { useSearchParams } from "react-router";
import type { CustomFieldEntityType, Id } from "../../types";
import { useAuth } from "../../features/auth/AuthProvider";
import { useI18n } from "../../lib/i18n";
import { useCustomFieldContext } from "./CustomEntityFields";
import { Button } from "../ui/Button";
import { ErrorState } from "../ui/StateViews";
import { CustomFieldFilterFields, validCustomFieldFilter } from "./CustomFieldFilterFields";

export const customFilterParams = (params: URLSearchParams) => ({
  custom_field: params.get("custom_field") || undefined,
  custom_operator: params.get("custom_operator") || undefined,
  custom_value: params.get("custom_value") || undefined,
});
type Preference = { order: string[]; hidden: string[] };
function readPreference(key: string): Preference {
  try { const saved = JSON.parse(localStorage.getItem(key) || "null");
    if (Array.isArray(saved?.order) && Array.isArray(saved?.hidden)) return { order: saved.order.filter((id: unknown) => typeof id === "string"), hidden: saved.hidden.filter((id: unknown) => typeof id === "string") };
  } catch { /* A blocked storage area does not prevent working with records. */ }
  return { order: [], hidden: [] };
}
export function useCustomColumns(business: Id, kind: CustomFieldEntityType, ids: Id[]) {
  const query = useCustomFieldContext(business, kind, ids); const { user } = useAuth(); const { t } = useI18n();
  const data = query.isError ? undefined : query.data;
  const valueByField = new Map((data?.values || []).map(value => [`${value.entity_id}:${value.definition}`, value.value_json.value]));
  const storageKey = `platforma.custom-columns:${user?.id}:${business}:${kind}`;
  const [saved, setSaved] = useState(() => ({ key: storageKey, value: readPreference(storageKey) }));
  const preference = saved.key === storageKey ? saved.value : readPreference(storageKey);
  const definitions = (data?.definitions || []).filter(field => (field.options_json.display as { in_table?: boolean } | undefined)?.in_table === true);
  const ordered = [...definitions].sort((a, b) => {
    const left = preference.order.indexOf(String(a.id)); const right = preference.order.indexOf(String(b.id));
    return (left < 0 ? definitions.length + definitions.indexOf(a) : left) - (right < 0 ? definitions.length + definitions.indexOf(b) : right);
  });
  const save = (next: Preference) => { setSaved({ key: storageKey, value: next }); try { localStorage.setItem(storageKey, JSON.stringify(next)); } catch { /* The current view remains usable without persistent preferences. */ } };
  const columns = ordered.filter(field => !preference.hidden.includes(String(field.id))).map(field => ({
    id: String(field.id), header: field.label, cell: (row: { id: Id }) => {
      const value = valueByField.get(`${row.id}:${field.id}`);
      return value === null || value === undefined || value === "" ? "—" : typeof value === "boolean" ? t(value ? "crmCard.yes" : "crmCard.no") : Array.isArray(value) ? value.join(", ") : String(value);
    },
  }));
  const columnControls = definitions.length ? <div className="space-y-1">{ordered.map((field, index) => <div key={field.id} className="flex items-center gap-2">
      <label className="flex flex-1 items-center gap-2"><input type="checkbox" checked={!preference.hidden.includes(String(field.id))} onChange={event => save({ ...preference, hidden: event.target.checked ? preference.hidden.filter(id => id !== String(field.id)) : [...preference.hidden, String(field.id)] })} />{field.label}</label>
      {[-1, 1].map(direction => <Button key={direction} size="sm" variant="ghost" aria-label={`${t(`importWorkspace.${direction < 0 ? "up" : "down"}`)}: ${field.label}`} disabled={index + direction < 0 || index + direction >= ordered.length} onClick={() => {
        const order = ordered.map(item => String(item.id)); [order[index], order[index + direction]] = [order[index + direction], order[index]]; save({ ...preference, order });
      }}>{direction < 0 ? <ArrowUp size={14} /> : <ArrowDown size={14} />}</Button>)}
    </div>)}</div> : null;
  const error = query.error ? <ErrorState error={query.error} action={<Button onClick={() => void query.refetch()}>{t("importWorkspace.reload")}</Button>} /> : null;
  const toolbar = <div className="space-y-2">
    {error}
    {columnControls && <details className="rounded-control border border-platforma-border px-3 py-2 text-sm"><summary className="cursor-pointer">{t("importWorkspace.columns")}</summary><div className="mt-2">{columnControls}</div></details>}
    <CustomFieldFilter definitions={data?.definitions || []} />
    {!!data?.definitions.length && <EntityExportButton key={`${business}:${kind}`} business={business} kind={kind} />}
  </div>;
  return { columns, toolbar, columnControls, error, definitions: data?.definitions || [] };
}

function CustomFieldFilter({ definitions }: { definitions: NonNullable<ReturnType<typeof useCustomFieldContext>["data"]>["definitions"] }) {
  const [params, setParams] = useSearchParams(); const { t } = useI18n();
  const label = (key: string) => t(`importWorkspace.${key}`);
  const [field, setField] = useState(params.get("custom_field") || "");
  const [operation, setOperation] = useState(params.get("custom_operator") || "equals");
  const [value, setValue] = useState(params.get("custom_value") || "");
  const appliedField = params.get("custom_field") || "";
  const appliedOperation = params.get("custom_operator") || "equals";
  const appliedValue = params.get("custom_value") || "";
  useEffect(() => {
    setField(appliedField);
    setOperation(appliedOperation);
    setValue(appliedValue);
  }, [appliedField, appliedOperation, appliedValue]);
  const available = definitions.filter(item => (item.options_json.display as { in_filters?: boolean } | undefined)?.in_filters);
  if (!available.length && !params.get("custom_field")) return null;
  const apply = (clear = false) => {
    const next = new URLSearchParams(params); ["custom_field", "custom_operator", "custom_value"].forEach(key => next.delete(key));
    if (!clear && field) { next.set("custom_field", field); next.set("custom_operator", operation); if (operation !== "is_empty") next.set("custom_value", value); }
    next.set("page", "1"); setParams(next);
    if (clear) { setField(""); setValue(""); setOperation("equals"); }
  };
  return <div className="flex flex-wrap items-end gap-2">
    <CustomFieldFilterFields definitions={definitions} className="flex flex-wrap items-end gap-2"
      value={{ custom_field: field, custom_operator: operation, custom_value: value }} onChange={patch => {
        if (patch.custom_field !== undefined) setField(patch.custom_field);
        if (patch.custom_operator !== undefined) setOperation(patch.custom_operator);
        if (patch.custom_value !== undefined) setValue(patch.custom_value);
      }} />
    <Button variant="secondary" disabled={!field || !validCustomFieldFilter({ custom_field: field, custom_operator: operation, custom_value: value }, definitions)} onClick={() => apply()}>{label("applyFilter")}</Button>
    {params.has("custom_field") && <Button variant="ghost" onClick={() => apply(true)}>{label("resetFilter")}</Button>}
  </div>;
}

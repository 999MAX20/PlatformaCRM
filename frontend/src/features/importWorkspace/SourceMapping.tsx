import { ImportErrorNotice } from "./ImportErrorNotice";
import { useQuery } from "@tanstack/react-query";
import { customFieldsApi } from "../../api/customFields";
import type { CustomFieldEntityType, Id } from "../../types";
import { ArrowDown, ArrowUp } from "lucide-react";
import type { ImportField, ImportSource, ImportEntity } from "../../api/importWorkspace";
import { importEntities } from "../../api/importWorkspace";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { useI18n } from "../../lib/i18n";
import { useAuth } from "../auth/AuthProvider";

export function SourceMapping({ source, fields, onChange, disabled, businessId }: {
  source: ImportSource; fields: Record<ImportEntity, string[]>; onChange: (source: ImportSource) => void; disabled: boolean; businessId: Id;
}) {
  const { t } = useI18n();
  const { user } = useAuth();
  const label = (key: string) => t(`importWorkspace.${key}`);
  const entityType = ({ clients: "client", services: "service", specialists: "specialist", appointments: "appointment" } as Record<ImportEntity, CustomFieldEntityType>)[source.entity_type];
  const definitions = useQuery({ queryKey: ["import-field-definitions", businessId, user?.id, entityType], queryFn: () => customFieldsApi.listByEntity(entityType, businessId) });
  const available = (!definitions.error ? definitions.data || [] : []).filter(field => field.is_active && ["text", "number", "date", "boolean", "select"].includes(field.field_type));
  const fieldLabel = (key: string) => key.startsWith("custom.") ? source.fields.find(field => `custom.${field.key}` === key)?.label || key : label(`field.${key}`);
  const updateField = (key: string, patch: Partial<ImportField>) => onChange({ ...source, fields: source.fields.map(field => field.key === key ? { ...field, ...patch } : field) });
  const keys = [...fields[source.entity_type], ...source.fields.map(field => `custom.${field.key}`)];
  const columns = source.columns;
  const move = (key: string, direction: number) => {
    const next = [...columns]; const index = next.indexOf(key); const target = index + direction;
    if (target < 0 || target >= next.length) return;
    [next[index], next[target]] = [next[target], next[index]];
    onChange({ ...source, columns: next });
  };
  const mapColumn = (header: string, target: string) => {
    const mapping = Object.fromEntries(Object.entries(source.mapping).filter(([, value]) => value !== header));
    let customFields = source.fields;
    if (target.startsWith("existing:")) {
      const definition = available.find(field => String(field.id) === target.slice(9));
      if (!definition) return;
      const display = definition.options_json.display as Partial<ImportField> | undefined;
      const field: ImportField = { key: definition.key, label: definition.label, definition_id: Number(definition.id),
        field_type: definition.field_type as ImportField["field_type"],
        options: (definition.options_json.options || []).map(item => typeof item === "string" ? item : item.value || item.key || item.label || ""),
        in_card: display?.in_card ?? true, in_table: display?.in_table ?? false, in_filters: display?.in_filters ?? false, in_calendar: display?.in_calendar ?? false };
      customFields = [...customFields.filter(item => item.key !== field.key), field]; target = `custom.${field.key}`;
    }
    if (target === "new") {
      let number = 1; while (customFields.some(field => field.key === `field_${number}`)) number++;
      const field: ImportField = { key: `field_${number}`, label: header, field_type: source.suggested_types[header] || "text", options: [], in_card: true, in_table: true, in_filters: false, in_calendar: false };
      customFields = [...customFields, field]; target = `custom.${field.key}`;
    }
    if (target) mapping[target] = header;
    const mapped = new Set(Object.keys(mapping));
    onChange({ ...source, mapping, fields: customFields.filter(field => mapped.has(`custom.${field.key}`)), columns: [...columns.filter(key => mapped.has(key)), ...(target && !columns.includes(target) ? [target] : [])] });
  };
  return <fieldset disabled={disabled} className="space-y-5">
    {definitions.error && <ImportErrorNotice error={definitions.error} action={<Button onClick={() => void definitions.refetch()}>{label("reload")}</Button>} />}
    <Button variant="secondary" onClick={() => {
      const mapping = { ...source.suggested_mapping[source.entity_type], ...source.mapping };
      const used = new Set<string>();
      const unique = Object.fromEntries(Object.entries(mapping).reverse().filter(([, header]) => {
        if (used.has(header)) return false;
        used.add(header); return true;
      }).reverse());
      onChange({ ...source, mapping: unique, columns: [...source.columns, ...Object.keys(unique).filter(key => !source.columns.includes(key))] });
    }}>{label("suggestions")}</Button>
    <Select label={label("entity")} value={source.entity_type} options={importEntities.map(value => ({ value, label: label(value) }))}
      onChange={event => { const entity_type = event.target.value as ImportEntity; const mapping = source.suggested_mapping[entity_type]; onChange({ ...source, entity_type, mapping, columns: Object.keys(mapping), fields: [], resolutions: {} }); }} />
    <div className="space-y-3">
      {source.headers.map(header => {
        const target = Object.keys(source.mapping).find(key => source.mapping[key] === header) || "";
        const custom = source.fields.find(field => `custom.${field.key}` === target);
        return <div key={header} className="rounded-control border border-platforma-border p-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="min-w-0 self-center break-words text-sm font-semibold text-platforma-text">{header}</div>
            <Select aria-label={`${header}: ${label("targetField")}`} value={target} portal options={[
              { value: "", label: label("skipColumn") }, ...keys.filter(key => !source.mapping[key] || source.mapping[key] === header).map(value => ({ value, label: fieldLabel(value) })),
              { value: "new", label: label("custom") },
              ...available.filter(field => !source.fields.some(item => item.key === field.key)).map(field => ({ value: `existing:${field.id}`, label: `${label("existingField")}: ${field.label}` })),
            ]} onChange={event => mapColumn(header, event.target.value)} />
          </div>
          {custom && <div className="mt-3 grid gap-3 border-t border-platforma-border pt-3 sm:grid-cols-2">
            <Input label={label("label")} value={custom.label} disabled={!!custom.definition_id} maxLength={128} onChange={event => updateField(custom.key, { label: event.target.value })} />
            <Select label={label("type")} value={custom.field_type} disabled={!!custom.definition_id} options={["text", "number", "date", "boolean", "select"].map(value => ({ value, label: label(value) }))} onChange={event => updateField(custom.key, { field_type: event.target.value as ImportField["field_type"] })} />
            {custom.field_type === "select" && <Input label={label("options")} value={custom.options.join(",")} disabled={!!custom.definition_id} onChange={event => updateField(custom.key, { options: event.target.value.split(",") })} />}
            <div className="flex flex-wrap items-center gap-3 sm:col-span-2">
              {(["in_card", "in_table", "in_filters", ...(source.entity_type === "appointments" ? ["in_calendar"] : [])] as ("in_card" | "in_table" | "in_filters" | "in_calendar")[]).map(key => <label key={key} className="flex items-center gap-2 text-sm"><input type="checkbox" disabled={!!custom.definition_id} checked={!!custom[key]} onChange={event => updateField(custom.key, { [key]: event.target.checked })} />{label(key)}</label>)}
            </div>
          </div>}
        </div>;
      })}
    </div>
    <section aria-label={label("columns")} className="space-y-2">
      <h3 className="text-sm font-semibold">{label("columns")}</h3>
      <p className="text-sm text-platforma-muted">{label("hiddenHint")}</p>
      {[...columns, ...Object.keys(source.mapping).filter(key => !columns.includes(key))].map(key => <div key={key} className="flex items-center gap-2">
        <label className="flex flex-1 items-center gap-2 text-sm"><input type="checkbox" checked={columns.includes(key)} onChange={event => onChange({ ...source, columns: event.target.checked ? [...columns, key] : columns.filter(item => item !== key) })} />{fieldLabel(key)}</label>
        <Button size="sm" variant="ghost" disabled={!columns.includes(key) || columns.indexOf(key) === 0} aria-label={`${label("up")}: ${fieldLabel(key)}`} onClick={() => move(key, -1)}><ArrowUp size={16} /></Button>
        <Button size="sm" variant="ghost" disabled={!columns.includes(key) || columns.indexOf(key) === columns.length - 1} aria-label={`${label("down")}: ${fieldLabel(key)}`} onClick={() => move(key, 1)}><ArrowDown size={16} /></Button>
      </div>)}
    </section>
  </fieldset>;
}

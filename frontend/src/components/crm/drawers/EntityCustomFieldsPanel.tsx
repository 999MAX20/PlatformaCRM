import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { getApiErrorMessage } from "../../../api/client";
import { customFieldValuesApi } from "../../../api/customFields";
import { useI18n } from "../../../lib/i18n";
import type { CrmCardPayload, CrmCardCustomField, CustomFieldEntityType, Id } from "../../../types";
import { Button } from "../../ui/Button";
import { Input } from "../../ui/Input";
import { Select } from "../../ui/Select";
import { ErrorState } from "../../ui/StateViews";
import { Textarea } from "../../ui/Textarea";
import { customFieldOptions } from "../../../lib/customFields";
import { drawerSurfaceClass } from "./shared";
import type { CrmDrawerEntity } from "./types";

export function EntityCustomFieldsPanel({ data, entity }: { data: CrmCardPayload; entity: CrmDrawerEntity }) {
  return <CustomFieldsEditor fields={data.custom_fields.filter(field => (field.definition.options_json.display as { in_card?: boolean } | undefined)?.in_card !== false)} entity={entity}
    businessId={data.client?.business || data.lead?.business || data.deal?.business || data.appointment?.business || 0} />;
}

export function CustomFieldsEditor({ fields, entity, businessId, onDirtyChange, onPendingChange, readOnly = false }: {
  fields: CrmCardCustomField[]; entity: { type: CustomFieldEntityType; id: Id }; businessId: Id;
  onDirtyChange?: (dirty: boolean) => void; readOnly?: boolean;
  onPendingChange?: (pending: boolean) => void;
}) {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [values, setValues] = useState<Record<number, unknown>>({});
  useEffect(() => {
    setValues({});
  }, [entity.type, entity.id]);

  useEffect(() => { onDirtyChange?.(Object.keys(values).length > 0); return () => onDirtyChange?.(false); }, [values, onDirtyChange]);

  const mutation = useMutation({
    mutationFn: () =>
      customFieldValuesApi.bulkUpsert({
        business: businessId,
        entity_type: entity.type,
        entity_id: String(entity.id),
        values: fields.filter((field) => field.can_edit && field.definition.id in values).map((field) => ({
          definition: field.definition.id,
          value_json: {
            value: values[field.definition.id],
          },
        })),
      }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["crm-card", entity.type, entity.id] }),
        queryClient.invalidateQueries({ queryKey: ["custom-field-context", businessId, entity.type] }),
      ]);
      setValues({});
    },
  });

  useEffect(() => { onPendingChange?.(mutation.isPending); return () => onPendingChange?.(false); }, [mutation.isPending, onPendingChange]);

  if (!fields.length) return null;

  return (
    <div className={drawerSurfaceClass}>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="font-semibold text-platforma-ink">{t("crmCard.customFields")}</h3>
          <p className="mt-1 text-sm text-platforma-muted">{t("crmCard.customFieldsText")}</p>
        </div>
        <Button type="button" variant="secondary" disabled={readOnly || !Object.keys(values).length || !fields.some((field) => field.can_edit)} isLoading={mutation.isPending} onClick={() => mutation.mutate()}>
          {t("crmCard.saveFields")}
        </Button>
      </div>
      {mutation.error ? <ErrorState error={mutation.error} message={getApiErrorMessage(mutation.error)} /> : null}
      <div className="grid gap-3 sm:grid-cols-2">
        {fields.map((field) => {
          const options = customFieldOptions(field.definition);
          const value = field.definition.id in values ? values[field.definition.id] : field.value?.value_json?.value;
          const disabled = readOnly || !field.can_edit || mutation.isPending;
          const change = (next: unknown) => setValues((current) => ({ ...current, [field.definition.id]: next }));
          if (field.definition.field_type === "boolean") {
            return (
              <Select
                key={field.definition.id}
                label={field.definition.label}
                disabled={disabled}
                value={value === true ? "true" : value === false ? "false" : ""}
                onChange={(event) => change(event.target.value === "" ? null : event.target.value === "true")}
                options={[
                  { value: "", label: t("crmCard.notSelected") },
                  { value: "false", label: t("crmCard.no") },
                  { value: "true", label: t("crmCard.yes") },
                ]}
              />
            );
          }
          if (field.definition.field_type === "select" && options.length) {
            return (
              <Select
                key={field.definition.id}
                label={field.definition.label}
                disabled={disabled}
                value={String(value ?? "")}
                onChange={(event) => change(event.target.value)}
                options={[{ value: "", label: t("crmCard.notSelected") }, ...options]}
              />
            );
          }
          if (field.definition.field_type === "multiselect") {
            const selected = Array.isArray(value) ? value.map(String) : [];
            return <fieldset key={field.definition.id} disabled={disabled} className="space-y-2">
              <legend className="mb-2 text-sm font-semibold text-platforma-subtle">{field.definition.label}</legend>
              {options.map((option) => <label key={option.value} className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={selected.includes(option.value)} onChange={(event) => change(event.target.checked ? [...selected, option.value] : selected.filter((item) => item !== option.value))} />
                {option.label}
              </label>)}
            </fieldset>;
          }
          if (field.definition.field_type === "textarea") {
            return <Textarea key={field.definition.id} label={field.definition.label} disabled={disabled} value={String(value ?? "")} onChange={(event) => change(event.target.value)} />;
          }
          let displayValue = String(value ?? "");
          if (field.definition.field_type === "datetime" && value) {
            const date = new Date(String(value));
            if (!Number.isNaN(date.getTime())) displayValue = new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
          }
          return (
            <Input
              key={field.definition.id}
              label={field.definition.label}
              disabled={disabled}
              step="any"
              type={field.definition.field_type === "number" || field.definition.field_type === "money" ? "number" : field.definition.field_type === "date" ? "date" : field.definition.field_type === "datetime" ? "datetime-local" : field.definition.field_type === "email" ? "email" : field.definition.field_type === "url" ? "url" : field.definition.field_type === "phone" ? "tel" : "text"}
              value={displayValue}
              onChange={(event) => change(field.definition.field_type === "datetime" && event.target.value ? new Date(event.target.value).toISOString() : event.target.value)}
            />
          );
        })}
      </div>
    </div>
  );
}

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, X } from "lucide-react";
import { useState } from "react";
import { getApiFieldErrors } from "../../../api/client";
import { customFieldsApi } from "../../../api/customFields";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import { customFieldOptions } from "../../../lib/customFields";
import { useI18n } from "../../../lib/i18n";
import type { CrmEntityType, CustomFieldDefinition, Id } from "../../../types";
import { slugify } from "../settingsUtils";
import { CustomFieldAccessMatrix, type FieldAccess } from "./CustomFieldAccessMatrix";
import { SettingsDrawer, SettingsFeedback, SettingsSaveBar } from "./SettingsLayout";

const types: CustomFieldDefinition["field_type"][] = ["text", "textarea", "number", "money", "date", "datetime", "select", "multiselect", "boolean", "phone", "email", "url"];
export const fieldEntities: CrmEntityType[] = ["client", "lead", "deal", "appointment"];

export function CustomFieldEditor({ initial, entity, businessId, open, onClose, onSaved }: { initial?: CustomFieldDefinition; entity: CrmEntityType; businessId: Id; open: boolean; onClose: () => void; onSaved: (field: CustomFieldDefinition) => void; }) {
  const { t } = useI18n();
  const cache = useQueryClient();
  const [draft, setDraft] = useState({ label: initial?.label || "", entity_type: initial?.entity_type || entity, field_type: initial?.field_type || "text", key: initial?.key || "", sort_order: initial?.sort_order || 0, is_active: initial?.is_active ?? true });
  const [options, setOptions] = useState(() => initial ? customFieldOptions(initial).map(option => option.value) : []);
  const [access, setAccess] = useState<FieldAccess>(() => {
    const view = initial?.permissions_json.view_roles || [];
    const edit = initial?.permissions_json.edit_roles || [];
    return { view, edit, allView: !view.length, allEdit: !edit.length };
  });
  const [roleError, setRoleError] = useState("");
  const [optionsError, setOptionsError] = useState("");
  const save = useMutation({
    mutationFn: (payload: Partial<CustomFieldDefinition>) => initial ? customFieldsApi.update({ id: initial.id, payload }) : customFieldsApi.create({ ...payload, business: businessId }),
    onSuccess: field => { void cache.invalidateQueries({ queryKey: ["custom-fields"] }); onSaved(field); },
  });
  const errors = getApiFieldErrors(save.error);
  const hasFieldError = ["label", "entity_type", "field_type", "permissions_json", ...(initial ? ["key", "sort_order", "is_active"] : []), ...(["select", "multiselect"].includes(draft.field_type) ? ["options_json"] : [])].some(key => errors[key]?.length);
  const hasOptions = ["select", "multiselect"].includes(draft.field_type);
  function change(values: Partial<typeof draft>) { setDraft(current => ({ ...current, ...values })); save.reset(); }
  function submit(event: React.FormEvent) {
    event.preventDefault();
    setRoleError(""); setOptionsError("");
    if ((!access.allView && !access.view.length) || (!access.allEdit && !access.edit.length)) {
      setRoleError(t("settings.redesign.noRolesSelected"));
      document.querySelector<HTMLElement>('[data-testid="field-access-matrix"]')?.focus();
      return;
    }
    const cleanOptions = options.map(value => value.trim());
    if (hasOptions && (cleanOptions.some(value => !value) || new Set(cleanOptions).size !== cleanOptions.length)) {
      setOptionsError(t("settings.redesign.uniqueOptions")); return;
    }
    const originalOptions = initial ? customFieldOptions(initial).map(option => option.value) : [];
    const changedOptions = JSON.stringify(cleanOptions) !== JSON.stringify(originalOptions);
    const optionValues = cleanOptions.map(value => initial?.options_json.options?.find(option => typeof option === "string" ? option === value : String(option.value ?? option.key ?? option.label) === value) || value);
    const payload: Partial<CustomFieldDefinition> = {
      ...draft,
      key: draft.key || slugify(draft.label).replace(/[^a-z0-9_-]/g, "").replace(/^[-_]+|[-_]+$/g, "").slice(0, 64) || "field_" + Date.now().toString(36),
      permissions_json: { view_roles: access.allView ? [] : access.view, edit_roles: access.allEdit ? [] : access.edit },
      ...(!initial || changedOptions && hasOptions ? { options_json: { ...initial?.options_json, options: optionValues } } : {}),
    };
    save.mutate(payload, { onError: () => window.requestAnimationFrame(() => document.querySelector<HTMLElement>('#settings-custom-field-form [aria-invalid="true"]')?.focus()) });
  }
  return <SettingsDrawer open={open} onClose={() => { if (!save.isPending) onClose(); }} title={t(initial ? "settings.edit" : "settings.redesign.newField")}
    footer={<SettingsSaveBar drawer feedback={<SettingsFeedback error={!hasFieldError ? save.error : undefined} />}>
      <Button type="button" variant="secondary" disabled={save.isPending} onClick={onClose}>{t("common.cancel")}</Button>
      <Button type="submit" form="settings-custom-field-form" isLoading={save.isPending}>{t(initial ? "common.save" : "settings.add")}</Button>
    </SettingsSaveBar>}>
    <form id="settings-custom-field-form" onSubmit={submit}>
      <fieldset disabled={save.isPending} className="space-y-4">
        <Input label={t("settings.redesign.name")} required value={draft.label} error={errors.label?.join(" ")} onChange={event => change({ label: event.target.value })} />
        <div className="grid gap-3 sm:grid-cols-2">
          <Select label={t("settings.entity")} value={draft.entity_type} error={errors.entity_type?.join(" ")} options={fieldEntities.map(value => ({ value, label: t(`settings.customFieldEntity.${value}`) }))} onChange={event => change({ entity_type: event.target.value as CrmEntityType })} />
          <Select label={t("settings.type")} value={draft.field_type} error={errors.field_type?.join(" ")} options={types.map(value => ({ value, label: t(`settings.customFieldType.${value}`) }))} onChange={event => change({ field_type: event.target.value as CustomFieldDefinition["field_type"] })} />
        </div>
        {hasOptions && <div className="space-y-2">
          <h3 className="text-sm font-semibold">{t("settings.options")}</h3>
          {options.map((value, index) => <div key={index} className="flex items-end gap-2">
            <div className="min-w-0 flex-1"><Input label={t("settings.redesign.option", { number: index + 1 })} value={value} required
              onChange={event => { setOptions(current => current.map((item, i) => i === index ? event.target.value : item)); setOptionsError(""); save.reset(); }} /></div>
            <Button variant="ghost" type="button" aria-label={t("settings.redesign.removeOption", { number: index + 1 })} onClick={() => { setOptions(current => current.filter((_, i) => i !== index)); setOptionsError(""); save.reset(); }}><X size={16} /></Button>
          </div>)}
          <Button type="button" variant="secondary" onClick={() => setOptions(current => [...current, ""])}><Plus size={16} />{t("settings.redesign.addOption")}</Button>
          {(optionsError || errors.options_json) && <p role="alert" className="text-sm text-platforma-danger">{optionsError || errors.options_json?.join(" ")}</p>}
        </div>}
        <div className="border-t border-platforma-border pt-4"><CustomFieldAccessMatrix value={access} onChange={next => { setAccess(next); setRoleError(""); save.reset(); }} error={roleError || errors.permissions_json?.join(" ")} /></div>
        {initial && <>
          <label className="flex min-h-11 items-center gap-3 text-sm"><input type="checkbox" className="h-5 w-5 accent-brand-500" checked={draft.is_active} onChange={event => change({ is_active: event.target.checked })} />{t("settings.customFieldActive")}</label>
          {errors.is_active && <p role="alert" className="text-sm text-platforma-danger">{errors.is_active.join(" ")}</p>}
          <details open={Boolean(errors.key || errors.sort_order) || undefined} className="border-t border-platforma-border pt-3">
            <summary className="platforma-focus-ring min-h-11 cursor-pointer py-2 text-sm font-semibold">{t("settings.technicalDetails")}</summary>
            <div className="space-y-3 py-3">
              <Input label={t("settings.fieldKey")} value={draft.key} required pattern="[a-zA-Z0-9_-]+" maxLength={64} error={errors.key?.join(" ")} onChange={event => change({ key: event.target.value })} />
              <Input label={t("settings.sortOrder")} type="number" step={1} value={draft.sort_order} error={errors.sort_order?.join(" ")} onChange={event => change({ sort_order: Number(event.target.value || 0) })} />
              <p className="text-xs text-platforma-subtle">{t("settings.customFieldRequiredMetadata")}: {t(initial.is_required ? "crmCard.yes" : "crmCard.no")}</p>
            </div>
          </details>
        </>}
      </fieldset>
    </form>
  </SettingsDrawer>;
}

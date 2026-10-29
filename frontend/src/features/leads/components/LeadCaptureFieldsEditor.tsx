import { useMutation } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { getApiFieldErrors } from "../../../api/client";
import { leadFormFieldsApi } from "../../../api/leadForms";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import { Textarea } from "../../../components/ui/Textarea";
import { ErrorState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import type { Id, LeadFormField } from "../../../types";
import { captureFieldOptions, captureOptionsPatch } from "../utils/captureFieldOptions";

const types: LeadFormField["field_type"][] = ["text", "textarea", "phone", "email", "select"];

export function LeadCaptureFieldsEditor({ form, initial, onSaved, onCancel, onBusyChange }: {
  form: Id; initial?: LeadFormField; onSaved: () => Promise<unknown>; onCancel: () => void; onBusyChange: (busy: boolean) => void;
}) {
  const { t } = useI18n();
  const [draft, setDraft] = useState({
    label: initial?.label ?? "", key: initial?.key ?? "", field_type: initial?.field_type ?? "text",
    placeholder: initial?.placeholder ?? "", is_required: initial?.is_required ?? false, sort_order: initial?.sort_order ?? 0,
  });
  const [options, setOptions] = useState(() => captureFieldOptions(initial?.options_json).map(option => option.value).join("\n"));
  const [optionsError, setOptionsError] = useState("");
  const save = useMutation({
    mutationFn: (payload: Partial<LeadFormField>) => initial ? leadFormFieldsApi.update({ id: initial.id, payload }) : leadFormFieldsApi.create({ ...payload, form }),
    onSuccess: onSaved,
  });
  useEffect(() => { onBusyChange(save.isPending); return () => onBusyChange(false); }, [onBusyChange, save.isPending]);
  const errors = getApiFieldErrors(save.error);
  const change = (patch: Partial<typeof draft>) => { setDraft(value => ({ ...value, ...patch })); save.reset(); };
  return <form onSubmit={event => {
    event.preventDefault();
    const values = options.split("\n").map(value => value.trim());
    if (draft.field_type === "select" && (values.some(value => !value) || new Set(values).size !== values.length)) {
      setOptionsError(t("settings.redesign.uniqueOptions")); return;
    }
    const optionsPatch = draft.field_type === "select" ? captureOptionsPatch(initial?.options_json, values) : undefined;
    save.mutate({ ...draft, ...(optionsPatch ? { options_json: optionsPatch } : {}) });
  }} className="space-y-4" data-testid="lead-capture-field-editor">
    <fieldset disabled={save.isPending} className="space-y-4">
      <Input label={t("captureFields.label")} value={draft.label} required maxLength={128} error={errors.label?.join(" ")}
        onChange={event => change({ label: event.target.value })} />
      <Input label={t("settings.fieldKey")} value={draft.key} required maxLength={64} pattern={"[a-zA-Z0-9_\\-]+"} error={errors.key?.join(" ")}
        onChange={event => change({ key: event.target.value })} />
      <Select label={t("settings.type")} value={draft.field_type} options={types.map(value => ({ value, label: t(`settings.customFieldType.${value}`) }))}
        error={errors.field_type?.join(" ")} onChange={event => change({ field_type: event.target.value as LeadFormField["field_type"] })} />
      {draft.field_type === "select" && <Textarea label={t("settings.options")} value={options} placeholder={t("captureFields.optionsHint")}
        error={optionsError || errors.options_json?.join(" ")} onChange={event => { setOptions(event.target.value); setOptionsError(""); save.reset(); }} />}
      <Input label={t("captureFields.placeholder")} value={draft.placeholder} maxLength={255} error={errors.placeholder?.join(" ")}
        onChange={event => change({ placeholder: event.target.value })} />
      <Input label={t("settings.sortOrder")} type="number" min={0} step={1} required value={draft.sort_order} error={errors.sort_order?.join(" ")}
        onChange={event => change({ sort_order: Number(event.target.value) })} />
      <label className="flex min-h-11 items-center gap-3 text-sm"><input type="checkbox" className="h-5 w-5 accent-brand-500"
        checked={draft.is_required} onChange={event => change({ is_required: event.target.checked })} />{t("captureFields.required")}</label>
      {save.isError && <ErrorState error={save.error} />}
      <div className="flex flex-wrap justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onCancel}>{t("common.cancel")}</Button>
        <Button type="submit" isLoading={save.isPending}>{t("common.save")}</Button>
      </div>
    </fieldset>
  </form>;
}

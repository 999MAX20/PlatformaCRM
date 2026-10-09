import { Plus } from "lucide-react";
import { useState } from "react";
import { Button } from "../../../components/ui/Button";
import type { CrmEntityType } from "../../../types";
import { CustomFieldEditor, fieldEntities } from "../components/CustomFieldEditor";
import { SettingsFeedback, SettingsSection, SettingsTabs } from "../components/SettingsLayout";
import { SettingsQueryState } from "../components/SettingsQueryState";
import type { SettingsModel } from "../useSettingsModel";

export function CustomFieldsSection({ model }: { model: SettingsModel; }) {
  const { t, activeSettingsSection, business, customFields, updateCustomFieldMutation, removeCustomFieldMutation, confirmDelete } = model;
  const [entity, setEntity] = useState<CrmEntityType>("client");
  const [editor, setEditor] = useState<"new" | number | null>(null);
  const initial = customFields.data?.find(field => Number(field.id) === editor);
  const rows = (customFields.data || []).filter(field => field.entity_type === entity);
  const pending = updateCustomFieldMutation.isPending || removeCustomFieldMutation.isPending;
  return <SettingsSection id="custom-fields" active={activeSettingsSection} title={t("settings.section.custom-fields")}
    actions={<Button type="button" disabled={pending} onClick={() => setEditor("new")}><Plus size={16} />{t("settings.redesign.addField")}</Button>}>
    <div className="space-y-4 p-4 sm:p-5">
      <SettingsTabs value={entity} onChange={setEntity} label={t("settings.entity")} items={fieldEntities.map(value => ({ value, label: t(`settings.customFieldEntity.${value}`) }))} />
      <SettingsQueryState queries={[customFields]} />
      {customFields.isSuccess && <div>
        <div className="hidden grid-cols-[minmax(0,1.4fr)_minmax(0,0.8fr)_minmax(0,0.6fr)_auto] gap-4 border-b border-platforma-border bg-surface-muted px-3 py-3 text-xs text-platforma-subtle xl:grid">
          <span>{t("settings.redesign.name")}</span><span>{t("settings.type")}</span><span>{t("settings.redesign.status")}</span><span />
        </div>
        {rows.map(field => <div key={field.id} className="border-b border-platforma-border px-3 py-4">
          <div className="grid items-center gap-3 xl:grid-cols-[minmax(0,1.4fr)_minmax(0,0.8fr)_minmax(0,0.6fr)_auto] xl:gap-4">
            <p className="text-sm font-semibold">{field.label}</p>
            <p className="text-sm text-platforma-subtle">{t(`settings.customFieldType.${field.field_type}`)}</p>
            <p className={"text-xs " + (field.is_active ? "text-platforma-success" : "text-platforma-subtle")}>{t(field.is_active ? "settings.active" : "settings.inactive")}</p>
            <div className="flex flex-wrap gap-2">
              <Button type="button" variant="secondary" disabled={pending} onClick={() => setEditor(Number(field.id))}>{t("settings.edit")}</Button>
              <Button type="button" variant={field.is_active ? "warning" : "secondary"} disabled={pending}
                onClick={() => updateCustomFieldMutation.mutate({ id: field.id, payload: { is_active: !field.is_active } })}>{t(field.is_active ? "settings.disable" : "settings.enable")}</Button>
              <Button type="button" variant="danger" disabled={pending} onClick={async () => { if (await confirmDelete(field.label)) removeCustomFieldMutation.mutate(field.id); }}>{t("settings.delete")}</Button>
            </div>
          </div>
          {updateCustomFieldMutation.variables?.id === field.id && <div className="mt-2"><SettingsFeedback error={updateCustomFieldMutation.error} saved={updateCustomFieldMutation.isSuccess} /></div>}
          {removeCustomFieldMutation.variables === field.id && <div className="mt-2"><SettingsFeedback error={removeCustomFieldMutation.error} /></div>}
        </div>)}
        {!rows.length && <p className="py-8 text-center text-sm text-platforma-subtle">{t("settings.noCustomFields")}</p>}
      </div>}
    </div>
    {business && (editor === "new" || initial) && <CustomFieldEditor key={editor} businessId={business.id} entity={entity} initial={initial}
      open={activeSettingsSection === "custom-fields"} onClose={() => setEditor(null)} onSaved={field => { setEntity(field.entity_type); setEditor(null); }} />}
  </SettingsSection>;
}

import { Pencil, Plus, Power, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router";
import { ActionMenu } from "../../../components/ui/ActionMenu";
import { Button } from "../../../components/ui/Button";
import { hasPermission } from "../../../lib/permissions";
import { useAuth } from "../../auth/AuthProvider";
import type { CrmEntityType } from "../../../types";
import { CustomFieldEditor, fieldEntities } from "../components/CustomFieldEditor";
import { SettingsFeedback, SettingsSection, SettingsTabs } from "../components/SettingsLayout";
import { SettingsQueryState } from "../components/SettingsQueryState";
import type { SettingsModel } from "../useSettingsModel";

const columns = "sm:grid-cols-[minmax(0,1.4fr)_minmax(0,0.8fr)_minmax(0,0.6fr)_44px]";
const entityLinks = { client: "/app/clients", lead: "/app/leads", deal: "/app/deals", appointment: "/app/calendar" };

export function CustomFieldsSection({ model }: { model: SettingsModel }) {
  const { t, activeSettingsSection, business, customFields, updateCustomFieldMutation, removeCustomFieldMutation, confirmDelete } = model;
  const { user } = useAuth();
  const [entity, setEntity] = useState<CrmEntityType>("client");
  const [editor, setEditor] = useState<"new" | number | null>(null);
  const initial = customFields.data?.find(field => Number(field.id) === editor);
  const rows = (customFields.data || []).filter(field => field.entity_type === entity);
  const pending = updateCustomFieldMutation.isPending || removeCustomFieldMutation.isPending;
  return <SettingsSection id="custom-fields" active={activeSettingsSection} title={t("settings.section.custom-fields")}
    actions={<Button type="button" disabled={pending} onClick={() => setEditor("new")}><Plus size={16} />{t("settings.redesign.addField")}</Button>}>
    <div className="space-y-4 p-4 sm:p-5">
      <SettingsTabs value={entity} onChange={setEntity} label={t("settings.entity")} items={fieldEntities.map(value => ({ value, label: t(`settings.customFieldEntity.${value}`) }))} />
      <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-platforma-subtle">
        <p className="max-w-2xl">{t(`settings.workflow.fieldPlacement.${entity}`)}</p>
        {hasPermission(user, business?.id, entity === "appointment" ? "appointments" : entity + "s", "view") && <Link to={entityLinks[entity]} className="platforma-focus-ring inline-flex min-h-11 items-center rounded-control font-semibold text-brand-700 underline underline-offset-4">{t(`settings.workflow.openEntities.${entity}`)}</Link>}
      </div>
      <SettingsQueryState queries={[customFields]} />
      {customFields.isSuccess && <div>
        <div data-testid="custom-fields-heading" className={`hidden gap-4 border-b border-platforma-border bg-surface-muted px-3 py-3 text-xs text-platforma-subtle sm:grid ${columns}`}>
          <span>{t("settings.redesign.name")}</span><span>{t("settings.type")}</span><span>{t("settings.redesign.status")}</span><span className="sr-only">{t("settings.workflow.fieldActions")}</span>
        </div>
        {rows.map(field => <div key={field.id} data-testid="custom-field-row" className="border-b border-platforma-border px-3 py-3">
          <div className={`grid grid-cols-[minmax(0,1fr)_44px] items-center gap-x-4 gap-y-2 ${columns}`}>
            <button type="button" className="platforma-focus-ring min-h-11 break-words rounded-control text-left text-sm font-semibold" disabled={pending} onClick={() => setEditor(Number(field.id))}>{field.label}</button>
            <p className="col-start-1 text-sm text-platforma-subtle sm:col-auto">{t(`settings.customFieldType.${field.field_type}`)}</p>
            <p className={`col-start-1 text-xs sm:col-auto ${field.is_active ? "text-platforma-success" : "text-platforma-subtle"}`}>{t(field.is_active ? "settings.active" : "settings.inactive")}</p>
            <div className="col-start-2 row-start-1 sm:col-auto sm:row-auto"><ActionMenu label={`${t("settings.workflow.fieldActions")} · ${field.label}`} disabled={pending} items={[
              { key: "edit", label: t("settings.edit"), icon: Pencil, onSelect: () => setEditor(Number(field.id)) },
              { key: "toggle", label: t(field.is_active ? "settings.disable" : "settings.enable"), icon: Power, tone: field.is_active ? "warning" : "neutral", onSelect: () => updateCustomFieldMutation.mutate({ id: field.id, payload: { is_active: !field.is_active } }) },
              { key: "delete", label: t("settings.delete"), icon: Trash2, tone: "danger", onSelect: async () => { if (await confirmDelete(field.label)) removeCustomFieldMutation.mutate(field.id); } },
            ]} /></div>
          </div>
          {updateCustomFieldMutation.variables?.id === field.id && <div className="mt-2"><SettingsFeedback error={updateCustomFieldMutation.error} saved={updateCustomFieldMutation.isSuccess} /></div>}
          {removeCustomFieldMutation.variables === field.id && <div className="mt-2"><SettingsFeedback error={removeCustomFieldMutation.error} /></div>}
        </div>)}
        {!rows.length && <p className="py-8 text-center text-sm text-platforma-subtle">{t("settings.workflow.fieldsEmpty")}</p>}
      </div>}
    </div>
    {business && (editor === "new" || initial) && <CustomFieldEditor key={editor} businessId={business.id} entity={entity} initial={initial}
      open={activeSettingsSection === "custom-fields"} onClose={() => setEditor(null)} onSaved={field => { setEntity(field.entity_type); setEditor(null); }} />}
  </SettingsSection>;
}

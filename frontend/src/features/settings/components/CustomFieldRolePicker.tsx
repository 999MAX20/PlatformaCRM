import { useI18n } from "../../../lib/i18n";
import { teamRoleOptions } from "../settingsConfig";

export function CustomFieldRolePicker({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  const { t } = useI18n();
  const selected = value.split(",").map((role) => role.trim()).filter(Boolean);
  const roles = [...new Set([...teamRoleOptions.map((option) => String(option.value)), ...selected])];
  return <fieldset className="space-y-2 rounded-card border border-platforma-border p-3">
    <legend className="px-1 text-sm font-semibold text-platforma-subtle">{label}</legend>
    <label className="flex items-center gap-2 text-sm">
      <input type="checkbox" checked={!selected.length} onChange={() => onChange("")} />
      {t("settings.allRoles")}
    </label>
    <div className="flex flex-wrap gap-x-4 gap-y-2">
      {roles.map((role) => <label key={role} className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={selected.includes(role)} onChange={(event) => onChange((event.target.checked ? [...selected, role] : selected.filter((item) => item !== role)).join(", "))} />
        {t(`settings.role.${role}`)}
      </label>)}
    </div>
  </fieldset>;
}

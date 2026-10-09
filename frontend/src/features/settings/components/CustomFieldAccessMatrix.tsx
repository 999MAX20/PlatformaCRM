import { useI18n } from "../../../lib/i18n";
import { teamRoleOptions } from "../settingsConfig";

export type FieldAccess = { allView: boolean; allEdit: boolean; view: string[]; edit: string[]; };

export function CustomFieldAccessMatrix({ value, onChange, error }: { value: FieldAccess; onChange: (value: FieldAccess) => void; error?: string; }) {
  const { t } = useI18n();
  const roles = [...new Set([...teamRoleOptions.map(option => String(option.value)), ...value.view, ...value.edit])];
  function toggle(role: string, kind: "view" | "edit", checked: boolean) {
    onChange({ ...value, [kind]: checked ? [...value[kind], role] : value[kind].filter(item => item !== role) });
  }
  return <fieldset className="space-y-3" tabIndex={-1} data-testid="field-access-matrix">
    <legend className="mb-3 text-sm font-bold">{t("settings.redesign.fieldAccess")}</legend>
    <div className="space-y-2">
      <label className="flex min-h-11 items-center gap-3 text-sm"><input type="checkbox" className="h-5 w-5 shrink-0 accent-brand-500" checked={value.allView}
        onChange={event => onChange({ ...value, allView: event.target.checked, view: !event.target.checked && !value.view.length ? roles : value.view })} />{t("settings.redesign.allViewRoles")}</label>
      <label className="flex min-h-11 items-center gap-3 text-sm"><input type="checkbox" className="h-5 w-5 shrink-0 accent-brand-500" checked={value.allEdit}
        onChange={event => onChange({ ...value, allEdit: event.target.checked, edit: !event.target.checked && !value.edit.length ? roles : value.edit })} />{t("settings.redesign.allEditRoles")}</label>
    </div>
    <table className="w-full table-fixed text-left text-sm">
      <thead className="bg-surface-muted text-xs text-platforma-subtle"><tr><th className="w-1/2 px-2 py-3 font-medium">{t("settings.role")}</th><th className="px-1 py-3 text-center font-medium">{t("settings.redesign.action.view")}</th><th className="px-1 py-3 text-center font-medium">{t("settings.redesign.action.update")}</th></tr></thead>
      <tbody className="divide-y divide-platforma-border">{roles.map(role => <tr key={role}>
        <th scope="row" className="break-words px-2 py-2 font-medium">{t(`settings.role.${role}`)}</th>
        {(["view", "edit"] as const).map(kind => <td key={kind} className="text-center">
          <label className="inline-flex h-11 w-11 items-center justify-center">
            <input type="checkbox" className="h-5 w-5 accent-brand-500" disabled={kind === "view" ? value.allView : value.allEdit}
              checked={(kind === "view" ? value.allView : value.allEdit) || value[kind].includes(role)}
              aria-label={t(`settings.role.${role}`) + " · " + t(`settings.redesign.action.${(kind === "view" ? "view" : "update")}`)}
              onChange={event => toggle(role, kind, event.target.checked)} />
          </label>
        </td>)}
      </tr>)}</tbody>
    </table>
    <p className="text-xs leading-5 text-platforma-subtle">{t("settings.redesign.fieldAccessNote")}</p>
    {error && <p role="alert" className="text-sm text-platforma-danger">{error}</p>}
  </fieldset>;
}

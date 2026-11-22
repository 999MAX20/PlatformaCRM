import { useState } from "react";
import { medicalRolesApi as api, type MedicalRoleAccess, type MedicalRoleKind, type MedicalRolePermission } from "../../../api/medicalRoles";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import { useI18n } from "../../../lib/i18n";
import { MedicalRoleCommand, type RoleFormControl } from "./MedicalRoleCommand";

export function MedicalRoleDefinitionForm({ businessId, access, control }: {
  businessId: number; access: MedicalRoleAccess; control: RoleFormControl;
}) {
  const { t } = useI18n();
  const [name, setName] = useState("");
  const [kind, setKind] = useState<MedicalRoleKind>("head");
  const [rules, setRules] = useState<Record<string, MedicalRolePermission>>({});
  const permissions = Object.entries(rules).sort(([a], [b]) => a.localeCompare(b)).map(([, value]) => value);
  const payload = name.trim() && permissions.length ? { business_id: businessId, name, kind, permissions } : null;
  return <MedicalRoleCommand payload={payload} dirty={Boolean(name || permissions.length || kind !== "head")} submit={api.create}
    label={t("medical.roles.create")} control={control}>
    <Input label={t("medical.roles.name")} value={name} maxLength={128} required onChange={event => setName(event.target.value)} />
    <Select label={t("medical.roles.kind")} value={kind} options={Object.keys(access.permissions_by_kind).map(value => ({ value, label: t(`medical.roles.kind.${value}`) }))}
      onChange={event => { if (!permissions.length || window.confirm(t("medical.clinical.discard"))) { setKind(event.target.value as MedicalRoleKind); setRules({}); } }} />
    <div className="divide-y divide-platforma-border">
      {access.permissions_by_kind[kind].map(group => <fieldset key={group.resource} className="min-w-0 space-y-2 py-3">
        <legend className="pt-3 text-sm font-semibold">{t(`medical.roles.resource.${group.resource}`)}</legend>
        {group.actions.map(action => {
          const key = `${group.resource}:${action}`;
          const rule = rules[key];
          return <div key={action} className="grid gap-2 sm:grid-cols-2 sm:items-center">
            <label className="flex min-h-11 cursor-pointer items-center gap-2 text-sm">
              <input type="checkbox" className="h-5 w-5 accent-brand-500" checked={!!rule} onChange={event => setRules(previous => {
                const next = { ...previous };
                if (event.target.checked) next[key] = { resource: group.resource, action, scope: "own" }; else delete next[key];
                return next;
              })} />{t(`medical.roles.action.${action}`)}
            </label>
            {rule ? <Select label={`${t("medical.roles.scope")}: ${t(`medical.roles.resource.${group.resource}`)} · ${t(`medical.roles.action.${action}`)}`}
              value={rule.scope} options={["own", "team", "business"].map(value => ({ value, label: t(`settings.visibility.${value}`) }))}
              onChange={event => setRules(previous => ({ ...previous, [key]: { ...rule, scope: event.target.value as MedicalRolePermission["scope"] } }))} /> : null}
          </div>;
        })}
      </fieldset>)}
    </div>
  </MedicalRoleCommand>;
}

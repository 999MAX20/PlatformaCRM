import { useCallback, useState } from "react";
import { medicalRolesApi as api, type MedicalRoleContext } from "../../../api/medicalRoles";
import { Select } from "../../../components/ui/Select";
import { Textarea } from "../../../components/ui/Textarea";
import { useI18n } from "../../../lib/i18n";
import { MedicalRoleCommand, type RoleFormControl } from "./MedicalRoleCommand";
import { MedicalRolePageStatus } from "./MedicalRolePageStatus";
import { useMedicalRolePage } from "./useMedicalRolePage";

export function MedicalRoleAssignmentForm({ businessId, context, control }: {
  businessId: number; context: MedicalRoleContext; control: RoleFormControl;
}) {
  const { t } = useI18n();
  const [roleId, setRoleId] = useState("");
  const [all, setAll] = useState(false);
  const [branches, setBranches] = useState<number[]>([]);
  const [reason, setReason] = useState("");
  const memberId = context.member.id;
  const readRoles = useCallback((after_id: number | undefined, signal: AbortSignal) => api.roles({ business_id: businessId, after_id }, signal), [businessId]);
  const readBranches = useCallback((after_id: number | undefined, signal: AbortSignal) => api.branches({ business_id: businessId, member_id: memberId, after_id }, signal), [businessId, memberId]);
  const roles = useMedicalRolePage(readRoles, control.onDenied);
  const available = useMedicalRolePage(readBranches, control.onDenied);
  const selected = roles.rows.find(role => String(role.id) === roleId && role.is_active);
  const payload = context.can_assign && selected && (all || branches.length > 0) && reason.trim() ? {
    business_id: businessId, member_id: memberId, role_id: selected.id, all_branches: all,
    branch_ids: all ? [] : [...branches].sort((a, b) => a - b), expected_revision: context.assignment?.revision ?? 0, reason,
  } : null;
  return <MedicalRoleCommand payload={payload} dirty={Boolean(roleId || all || branches.length || reason)} submit={api.assign}
    label={t("medical.roles.assign")} control={control}>
    <Select label={t("medical.roles.role")} value={roleId} onChange={event => setRoleId(event.target.value)}
      options={[{ value: "", label: t("common.select") }, ...roles.rows.filter(role => role.is_active).map(role => ({ value: role.id, label: role.name }))]} />
    <MedicalRolePageStatus page={roles} empty={t("medical.roles.noRoles")} />
    {selected ? <ul className="space-y-1 text-sm" aria-label={t("medical.roles.permissions")}>
      {selected.permissions.filter(rule => rule.is_allowed).map(rule => <li key={`${rule.resource}:${rule.action}`} className="break-words">
        {t(`medical.roles.resource.${rule.resource}`)} · {t(`medical.roles.action.${rule.action}`)} · {t(`settings.visibility.${rule.scope}`)}
      </li>)}
    </ul> : null}
    <fieldset className="min-w-0 space-y-2">
      <legend className="text-sm font-semibold">{t("medical.roles.branches")}</legend>
      <label className="flex min-h-11 cursor-pointer items-center gap-2 text-sm">
        <input type="checkbox" className="h-5 w-5 accent-brand-500" checked={all} disabled={!context.can_assign_all_branches}
          onChange={event => setAll(event.target.checked)} />{t("branches.allFuture")}
      </label>
      {!all ? available.rows.map(branch => <label key={branch.id} className="flex min-h-11 cursor-pointer items-center gap-2 break-words text-sm">
        <input type="checkbox" className="h-5 w-5 shrink-0 accent-brand-500" checked={branches.includes(branch.id)}
          onChange={event => setBranches(previous => event.target.checked ? [...previous, branch.id] : previous.filter(id => id !== branch.id))} />{branch.name}
      </label>) : null}
      {!all ? <MedicalRolePageStatus page={available} empty={t("medical.roles.noBranches")} /> : null}
    </fieldset>
    <Textarea label={t("medical.roles.reason")} required maxLength={2000} value={reason} onChange={event => setReason(event.target.value)} />
  </MedicalRoleCommand>;
}

export function MedicalRoleRevokeForm({ businessId, context, control }: { businessId: number; context: MedicalRoleContext; control: RoleFormControl }) {
  const { t } = useI18n();
  const [reason, setReason] = useState("");
  const payload = context.can_revoke && context.assignment && reason.trim() ? {
    business_id: businessId, member_id: context.member.id, expected_revision: context.assignment.revision, reason,
  } : null;
  return <MedicalRoleCommand payload={payload} dirty={Boolean(reason)} submit={api.revoke} label={t("medical.roles.revoke")} control={control}>
    <Textarea label={t("medical.roles.reason")} required maxLength={2000} value={reason} onChange={event => setReason(event.target.value)} />
  </MedicalRoleCommand>;
}

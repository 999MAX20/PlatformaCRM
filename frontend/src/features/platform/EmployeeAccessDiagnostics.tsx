import type { AccessInvitation, AccessMember } from "../../api/employeeAccess";
import { useI18n } from "../../lib/i18n";
import { formatDateTime } from "../../lib/format";

export type AccessTarget = { kind: "member"; row: AccessMember } | { kind: "invitation"; row: AccessInvitation };

export function EmployeeAccessDiagnostics({ target }: { target: AccessTarget }) {
  const { t } = useI18n();
  const roleName = target.kind === "member" && target.row.business_role ? target.row.business_role.name : t(`settings.role.${target.row.role}`);
  return <div className="space-y-3 text-sm" data-testid="access-diagnostics">
    <h3 className="font-semibold">{target.row.name}</h3>
    <p className="break-all">{target.row.email}</p>
    <p>{t("employeeAccess.role")}: {roleName}</p>
    {target.row.protected && <p role="status">{t("employeeAccess.protected")}</p>}
    {target.kind === "member" ? <>
      <dl className="grid gap-2 sm:grid-cols-2">
        <div><dt className="text-platforma-subtle">{t("employeeAccess.account")}</dt><dd>{t(target.row.account_active ? "employeeAccess.active" : "employeeAccess.inactive")}</dd></div>
        <div><dt className="text-platforma-subtle">{t("employeeAccess.membership")}</dt><dd>{t(target.row.membership_active ? "employeeAccess.active" : "employeeAccess.inactive")}</dd></div>
        {target.row.business_role && <div><dt className="text-platforma-subtle">{t("employeeAccess.role")}</dt><dd>{t(target.row.business_role.active ? "employeeAccess.roleActive" : "employeeAccess.roleInactive")}</dd></div>}
        {Object.entries(target.row.dependencies).map(([kind, count]) => <div key={kind}><dt className="text-platforma-subtle">{t(`clinicCrm.kind.${kind}`)}</dt><dd>{count}</dd></div>)}
      </dl>
      {!target.row.account_active && <p role="status">{t("employeeAccess.globalDisabled")}</p>}
      <div className="space-y-2"><h4 className="font-medium">{t("employeeAccess.specialists")}</h4>
        {!target.row.specialists.length && <p className="text-platforma-subtle">{t("employeeAccess.noSpecialist")}</p>}
        {target.row.specialists.map(row => <p key={row.id}>{row.name} · {t(row.is_active ? "employeeAccess.active" : "employeeAccess.inactive")} · {t("clinicCrm.kind.appointments")}: {row.appointments}</p>)}
      </div>
    </> : <dl className="grid gap-2 sm:grid-cols-2">
      <div><dt className="text-platforma-subtle">{t("employeeAccess.invitation")}</dt><dd>{t(`employeeAccess.invitation.${target.row.status}`)}</dd></div>
      <div><dt className="text-platforma-subtle">{t("recovery.expires")}</dt><dd>{formatDateTime(target.row.expires_at)}</dd></div>
    </dl>}
  </div>;
}

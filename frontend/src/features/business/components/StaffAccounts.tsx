import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";
import { teamApi } from "../../../api/team";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import { hasPermission } from "../../../lib/permissions";
import type { Id } from "../../../types";
import { useAuth } from "../../auth/AuthProvider";
import { RoleAccessPreview } from "../../settings/components/RoleAccessPreview";
import { TeamAccessControl } from "../../settings/components/TeamAccessControl";
import { settingsRoleName } from "../../settings/roleAccess";

export function StaffAccounts({ businessId, linkedUser }: { businessId: Id; linkedUser?: Id | null }) {
  const { t } = useI18n();
  const { user } = useAuth();
  const canView = hasPermission(user, businessId, "team", "view");
  const canManage = hasPermission(user, businessId, "team", "manage");
  const [selected, setSelected] = useState("");
  const [search, setSearch] = useState("");
  const members = useQuery({ queryKey: ["team-members", businessId], queryFn: () => teamApi.allMembers(businessId), enabled: canView });
  const roles = useQuery({ queryKey: ["team-roles", businessId], queryFn: () => teamApi.allRoles(businessId), enabled: canView });
  if (!canView) return null;
  if (members.isPending || roles.isPending) return <LoadingState />;
  if (members.error || roles.error) return <ErrorState error={members.error || roles.error} action={<Button onClick={() => void Promise.all([members.refetch(), roles.refetch()])}>{t("common.retry")}</Button>} />;
  const rows = (members.data || []).filter(member => `${member.user.full_name} ${member.user.email}`.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase()));
  const member = linkedUser !== undefined ? members.data?.find(item => item.user.id === linkedUser) : rows.find(item => String(item.id) === selected) || rows[0];
  const role = roles.data?.find(item => item.id === member?.business_role) || roles.data?.find(item => item.preset_key === member?.role);
  return <section className="space-y-4">
    <h3 className="text-sm font-semibold">{t("settings.section.team-access")}</h3>
    {linkedUser === undefined && <>
      <Input label={t("resources.searchPlaceholder")} value={search} onChange={event => setSearch(event.target.value)} />
      <Select label={t("business.staff")} value={member?.id || ""} options={rows.map(item => ({ value: item.id, label: item.user.full_name || item.user.email }))} onChange={event => setSelected(event.target.value)} />
    </>}
    {member ? <>
      <div className="space-y-1 text-sm"><p className="font-semibold">{member.user.full_name || member.user.email}</p>
        <p className="break-all text-platforma-subtle">{member.user.email}</p>
        <p>{role ? settingsRoleName(role, t) : t(`settings.role.${member.role}`)} · {t(member.is_active ? "branches.active" : "branches.paused")}</p>
      </div>
      <TeamAccessControl member={member} canManage={canManage} />
      <details className="rounded-control border border-platforma-border p-3"><summary className="platforma-focus-ring cursor-pointer text-sm font-semibold">{t("business.permissions")}</summary><div className="mt-3"><RoleAccessPreview role={role} baseRole={roles.data?.find(item => item.is_system && item.preset_key === member.role)} /></div></details>
    </> : <p className="text-sm text-platforma-subtle">{t("resources.noLinkedUser")}</p>}
    {canManage && <Link className="platforma-focus-ring inline-flex min-h-11 items-center text-sm font-semibold text-brand-700 underline" to="/app/settings#team-access">{t("business.manageAccounts")}</Link>}
  </section>;
}

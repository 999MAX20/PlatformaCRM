import { useQuery } from "@tanstack/react-query";
import { teamApi } from "../../../api/team";
import { useI18n } from "../../../lib/i18n";
import { permissionResourceLabel } from "../../../lib/permissions";
import type { BusinessRole } from "../../../types";
import { configuredRoleScope, roleActionLabel } from "../roleAccess";
import { translatedVisibilityLabel } from "../settingsUtils";
import { SettingsQueryState } from "./SettingsQueryState";

export function RoleAccessPreview({ role, baseRole }: { role?: BusinessRole; baseRole?: BusinessRole; }) {
  const { t } = useI18n();
  const catalog = useQuery({ queryKey: ["team-permission-catalog"], queryFn: teamApi.catalog, enabled: Boolean(role), staleTime: 300_000 });
  if (!role) return <p className="text-sm text-platforma-subtle">{t("settings.noRoles")}</p>;
  return <div className="space-y-3">
    <SettingsQueryState queries={[catalog]} />
    {role.preset_key === "owner" ? <p className="text-sm text-platforma-subtle">{t("settings.redesign.ownerAccess")}</p> : catalog.isSuccess && <div className="divide-y divide-platforma-border">
      {catalog.data.resources.map(({ resource, actions }) => {
        const allowed = actions.map(action => ({ action, scope: configuredRoleScope(role, resource, action, baseRole) })).filter(item => item.scope !== "none");
        return <div key={resource} className="grid gap-1 py-2.5 text-sm sm:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
          <p className="font-semibold">{permissionResourceLabel(resource, t)}</p>
          <div className="min-w-0 text-platforma-subtle">{allowed.length ? allowed.map(item => <p key={item.action}>{roleActionLabel(item.action, t)} · {item.scope ? translatedVisibilityLabel(item.scope, t) : t("settings.redesign.permissionInherited")}</p>) : translatedVisibilityLabel("none", t)}</div>
        </div>;
      })}
    </div>}
    <p className="text-xs leading-5 text-platforma-subtle">{t("settings.redesign.roleScopeNote")}</p>
  </div>;
}

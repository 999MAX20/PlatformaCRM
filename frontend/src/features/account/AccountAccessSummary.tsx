import { useActiveBusiness } from "../../hooks/useBusiness";
import { useI18n } from "../../lib/i18n";
import { businessRoleLabel, getActiveMembership, getPermissionScope, hasPermission, permissionResourceLabel, resourceLabels } from "../../lib/permissions";
import { useAuth } from "../auth/AuthProvider";

export function AccountAccessSummary() {
  const { user } = useAuth();
  const { business } = useActiveBusiness();
  const { t } = useI18n();
  const membership = getActiveMembership(user, business?.id);
  if (!membership) return null;
  const resources = Object.keys(resourceLabels).filter((resource) => hasPermission(user, business?.id, resource) && getPermissionScope(user, business?.id, resource) !== "none");

  return (
    <details className="mt-4 border-t border-platforma-border pt-3" data-testid="account-access-summary">
      <summary className="cursor-pointer text-sm font-semibold">{t("account.roleAccess")}</summary>
      <p className="mt-3 text-sm font-semibold">{business?.name} · {membership.business_role_name || businessRoleLabel(membership.role, t)}</p>
      <p className="mt-3 text-xs text-platforma-subtle">{t("account.availableSections")}</p>
      <dl className="mt-2 grid gap-x-6 gap-y-2 sm:grid-cols-2">
        {resources.map((resource) => (
          <div key={resource} className="flex flex-wrap justify-between gap-x-3 gap-y-1 text-sm">
            <dt>{permissionResourceLabel(resource, t)}</dt>
            <dd className="text-platforma-subtle">{t(`account.accessScope.${getPermissionScope(user, business?.id, resource)}`)}</dd>
          </div>
        ))}
      </dl>
    </details>
  );
}

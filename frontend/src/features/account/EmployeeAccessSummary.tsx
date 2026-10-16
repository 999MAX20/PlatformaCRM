import type { ReactNode } from "react";
import type { AccessRepair } from "../../api/employeeAccess";
import { Card } from "../../components/ui/Card";
import { useI18n } from "../../lib/i18n";
import { formatDateTime } from "../../lib/format";

export function EmployeeAccessSummary({ item, children }: { item: AccessRepair; children?: ReactNode }) {
  const { t } = useI18n();
  return <Card padding="md" className="space-y-3 break-words" data-testid="access-request" data-request-id={item.id}>
    <h3 className="font-semibold">{item.target_name} · {item.business_name}</h3>
    <p className="text-sm break-all">{item.target_email}</p>
    <dl className="grid gap-2 text-sm sm:grid-cols-2">
      <div><dt className="text-platforma-subtle">{t("employeeAccess.action")}</dt><dd>{t(`employeeAccess.action.${item.action}`)}</dd></div>
      <div><dt className="text-platforma-subtle">{t("recovery.state")}</dt><dd>{t(`employeeAccess.status.${item.status}`)}</dd></div>
      <div><dt className="text-platforma-subtle">{t("employeeAccess.role")}</dt><dd>{item.target_role?.name || t(`settings.role.${item.target_role_key}`)}</dd></div>
      <div><dt className="text-platforma-subtle">{t("recovery.expires")}</dt><dd>{formatDateTime(item.expires_at)}</dd></div>
      {item.owner_required && <div><dt className="text-platforma-subtle">{t("recovery.ownerConfirmation")}</dt><dd>{t(item.owner_confirmed_at ? "recovery.confirmed" : "recovery.waitingOwner")}</dd></div>}
      <div><dt className="text-platforma-subtle">{t("employeeAccess.preparedBy")}</dt><dd>{item.prepared_by}</dd></div>
      {item.executed_by && <div><dt className="text-platforma-subtle">{t("employeeAccess.executedBy")}</dt><dd>{item.executed_by} · {formatDateTime(item.completed_at)}</dd></div>}
    </dl>
    <p className="text-sm whitespace-pre-wrap">{item.reason}</p>
    {item.action === "reissue" && item.status === "completed" && <p role="status" className="text-sm">{t("employeeAccess.linkReady")}</p>}
    {children}
  </Card>;
}

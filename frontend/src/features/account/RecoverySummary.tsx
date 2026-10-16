import type { ReactNode } from "react";
import type { RecoveryRequest } from "../../api/recovery";
import { Card } from "../../components/ui/Card";
import { useI18n } from "../../lib/i18n";
import { formatDateTime } from "../../lib/format";

export function RecoverySummary({ item, children }: { item: RecoveryRequest; children?: ReactNode }) {
  const { t } = useI18n();
  return <Card padding="md" className="space-y-3 break-words" data-testid="recovery-request">
    <h3 className="font-semibold">{item.user_name} · {item.business_name}</h3>
    <dl className="grid gap-2 text-sm sm:grid-cols-2">
      <div><dt className="text-platforma-subtle">{t("recovery.newEmail")}</dt><dd>{item.new_email}</dd></div>
      <div><dt className="text-platforma-subtle">{t("recovery.state")}</dt><dd>{t(`recovery.status.${item.status}`)}</dd></div>
      <div><dt className="text-platforma-subtle">{t("recovery.delivery")}</dt><dd>{t(`recovery.delivery.${item.delivery_status}`)}</dd></div>
      <div><dt className="text-platforma-subtle">{t("recovery.expires")}</dt><dd>{formatDateTime(item.expires_at)}</dd></div>
      {item.owner_required && <div><dt className="text-platforma-subtle">{t("recovery.ownerConfirmation")}</dt><dd>{t(item.owner_confirmed_at ? "recovery.confirmed" : "recovery.waitingOwner")}</dd></div>}
      {item.verified_reference && <div><dt className="text-platforma-subtle">{t("recovery.reference")}</dt><dd>{item.verified_reference}</dd></div>}
    </dl>
    {item.reason && <p className="text-sm">{item.reason}</p>}
    {children}
  </Card>;
}

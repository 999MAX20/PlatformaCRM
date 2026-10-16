import type { ReactNode } from "react";
import type { OwnershipTransfer } from "../../api/ownership";
import { Card } from "../../components/ui/Card";
import { useI18n } from "../../lib/i18n";
import { supportDate } from "../support/SupportUI";

export function OwnershipTransferSummary({ item, children }: { item: OwnershipTransfer; children?: ReactNode }) {
  const { t, language } = useI18n();
  return <Card padding="md" data-testid="ownership-request" className="space-y-3">
    <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="break-words font-semibold">{item.business.name}</h3><span className="text-sm" role="status">{t(`ownership.status.${item.status}`)}</span></div>
    <dl className="grid gap-3 text-sm sm:grid-cols-2">
      <div className="min-w-0"><dt className="text-platforma-subtle">{t("ownership.previousOwner")}</dt><dd className="break-words font-medium">{item.previous_owner.name}</dd><dd className="break-all text-platforma-subtle">{item.previous_owner.email}</dd></div>
      <div className="min-w-0"><dt className="text-platforma-subtle">{t("ownership.newOwner")}</dt><dd className="break-words font-medium">{item.new_owner.name}</dd><dd className="break-all text-platforma-subtle">{item.new_owner.email}</dd></div>
      <div className="sm:col-span-2"><dt className="text-platforma-subtle">{t("ownership.previousAccess")}</dt><dd className="break-words">{item.previous_owner_business_role?.name || t("ownership.disableAccess")}</dd></div>
      <div><dt className="text-platforma-subtle">{t("ownership.previousConsent")}</dt><dd>{item.previous_owner_confirmed_at ? supportDate(item.previous_owner_confirmed_at, language, item.business.timezone) : t("ownership.awaiting")}</dd></div>
      <div><dt className="text-platforma-subtle">{t("ownership.newConsent")}</dt><dd>{item.new_owner_confirmed_at ? supportDate(item.new_owner_confirmed_at, language, item.business.timezone) : t("ownership.awaiting")}</dd></div>
    </dl>
    <p className="break-words text-sm">{item.reason}</p>
    <p className="text-xs text-platforma-subtle">{t("ownership.expires", { date: supportDate(item.expires_at, language, item.business.timezone) })}</p>
    {item.status === "pending" && <p className="text-sm text-platforma-subtle">{t("ownership.sessionEffect")}</p>}
    {children}
  </Card>;
}

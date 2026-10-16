import type { ReactNode } from "react";
import { Link } from "react-router";
import type { BillingOrder } from "../../api/billingCommerce";
import { Card } from "../../components/ui/Card";
import { useI18n } from "../../lib/i18n";

export function BillingOrderCard({ order, children, platform = false }: { order: BillingOrder; children?: ReactNode; platform?: boolean }) {
  const { t, language } = useI18n();
  const date = (value: string) => `${new Date(value).toLocaleString(language, { timeZone: "UTC" })} UTC`;
  return <Card padding="md" className="min-w-0 space-y-3" data-order-id={order.id}>
    <h3 className="font-semibold">{order.plan} · {order.amount} {order.currency}</h3>
    <p className="break-all text-xs text-platforma-subtle">{t("commerce.order")} {order.id}</p>
    <dl className="grid gap-x-4 gap-y-2 text-sm sm:grid-cols-2">
      <div><dt className="text-platforma-subtle">{t("commerce.period")}</dt><dd>{date(order.period_start)} — {date(order.period_end)}</dd></div>
      <div><dt className="text-platforma-subtle">{t("commerce.buyer")}</dt><dd>{order.buyer.name} · {t(`commerce.buyer.${order.buyer.kind}`)}</dd></div>
      <div><dt className="text-platforma-subtle">{t("commerce.payment")}</dt><dd>{t(`commerce.state.${order.payment_status}`)}</dd></div>
      <div><dt className="text-platforma-subtle">{t("commerce.application")}</dt><dd>{t(`commerce.state.${order.application_status}`)}</dd></div>
    </dl>
    {order.application_code && <p role="status" className="text-sm">{t(`commerce.code.${order.application_code}`)}</p>}
    {!platform && order.payment_status === "awaiting" && <details>
      <summary className="platforma-focus-ring cursor-pointer py-2 text-sm font-medium">{t("commerce.bankDetails")}</summary>
      {order.seller.iban ? <dl className="space-y-1 break-words text-sm">
        {["name", "tax_id", "bank", "iban", "bic"].map(key => <div key={key}><dt className="inline text-platforma-subtle">{t(`commerce.seller.${key}`)}: </dt><dd className="inline">{order.seller[key]}</dd></div>)}
        <div><dt className="inline text-platforma-subtle">{t("commerce.reference")}: </dt><dd className="inline break-all">{order.id}</dd></div>
      </dl> : <p role="status">{t("commerce.unavailable")}</p>}
    </details>}
    {order.attempts.map(attempt => <p key={attempt.id} className="text-sm" role="status">{t("commerce.card")}: {t(`commerce.state.${attempt.status}`)}</p>)}
    {order.receipts.length > 0 && <details><summary className="platforma-focus-ring cursor-pointer py-2 text-sm">{t("commerce.receipts")} ({order.receipt_count})</summary>
      <ul className="space-y-2 text-sm">{order.receipts.map(row => <li key={row.id} className="break-words">
        {t(`commerce.${row.source}`)} · {row.amount} {row.currency} · {t(`commerce.state.${row.status}`)} · {date(row.received_at)}
        {platform && row.reference && <p>{t("commerce.bankReference")}: {row.reference}</p>}
        {platform && row.reason && <p>{row.reason}</p>}
      </li>)}</ul></details>}
    <details><summary className="platforma-focus-ring cursor-pointer py-2 text-sm">{t("commerce.history")}</summary>
      <ul className="space-y-2 text-sm">{order.events.map((event, index) => <li key={index}>{date(event.created_at)} · {t(`commerce.event.${event.kind}`)}
        {event.code && <p>{t(`commerce.code.${event.code}`)}</p>}{platform && event.reason && <p>{event.reason}</p>}
        {platform && event.support_case_id && <Link className="platforma-focus-ring text-brand-700" to={`/platform/support/${event.support_case_id}`}>{t("businessDetails.caseId")} #{event.support_case_id}</Link>}
      </li>)}</ul></details>
    {children}
  </Card>;
}

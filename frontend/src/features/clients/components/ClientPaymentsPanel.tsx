import { useQuery } from "@tanstack/react-query";
import { paymentsApi } from "../../../api/payments";
import { Button } from "../../../components/ui/Button";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { formatDateTime } from "../../../lib/format";
import { useI18n } from "../../../lib/i18n";
import { PaymentsButton } from "../../payments/PaymentsButton";
import type { Client } from "../../../types";

export function ClientPaymentsPanel({ client, userId, timeZone }: { client: Client; userId: number; timeZone: string }) {
  const { t, language } = useI18n();
  const query = useQuery({ queryKey: ["client-payments", "client-page", client.business, client.id, userId],
    queryFn: () => paymentsApi.list({ business: client.business, client: client.id, page: 1, q: "", kind: "" }) });
  if (query.isPending) return <LoadingState />;
  if (query.error) return <ErrorState error={query.error} action={<Button variant="secondary" onClick={() => void query.refetch()}>{t("common.retry")}</Button>} />;
  return <section className="entity-page-section"><h2>{t("payments.title")}</h2>
    {query.data.results.length ? <div className="entity-visit-list">{query.data.results.map(item => <div className="entity-visit-row" key={item.id}>
      <span>{formatDateTime(item.occurred_at, timeZone, true, language)}</span><span>{t(item.kind === "receipt" ? "payments.receipt" : "payments.refundKind")}</span><span>{item.note}</span><strong>{item.amount} {item.currency}</strong>
    </div>)}</div> : <p className="entity-empty">{t("clients.pageNoPayments")}</p>}
    <PaymentsButton client={client} />
  </section>;
}

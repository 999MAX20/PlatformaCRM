import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { paymentsApi, type Payment, type PaymentOption } from "../../api/payments";
import { getApiErrorMessage } from "../../api/client";
import { useSearchParams } from "react-router";
import { clientsApi } from "../../api/clients";
import { usePageHeader } from "../../components/layout/PageHeaderContext";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { EmptyState, ErrorState, ForbiddenState, LoadingState } from "../../components/ui/StateViews";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useAuth } from "../auth/AuthProvider";
import { hasPermission } from "../../lib/permissions";
import { useI18n } from "../../lib/i18n";
import { formatDateTime } from "../../lib/format";
import { PaymentForm } from "./PaymentForm";

export function PaymentsPage() {
  const { business, isLoading, error } = useActiveBusiness();
  const { user } = useAuth();
  const { t } = useI18n();
  const [params] = useSearchParams();
  const clientId = params.get("client");
  const allowed = hasPermission(user, business?.id, "payments") && hasPermission(user, business?.id, "clients");
  const client = useQuery({
    queryKey: ["payments-client", business?.id, clientId],
    queryFn: () => clientsApi.get(Number(clientId)),
    enabled: allowed && clientId !== null && /^[1-9]\d*$/.test(clientId),
  });
  if (isLoading) return <LoadingState />;
  if (error) return <ErrorState error={error} />;
  if (!allowed || !business || (clientId !== null && !/^[1-9]\d*$/.test(clientId))) return <ForbiddenState />;
  if (clientId && client.isPending) return <LoadingState />;
  if (client.error) return <ErrorState error={client.error} action={<Button variant="secondary" onClick={() => void client.refetch()}>{t("common.retry")}</Button>} />;
  return <PaymentsWorkspace key={`${business.id}-${user?.id}-${clientId || "all"}`} client={client.data ? { id: client.data.id, label: client.data.full_name } : undefined} />;
}

function PaymentsWorkspace({ client }: { client?: PaymentOption }) {
  const { t } = useI18n();
  const { business } = useActiveBusiness();
  const { user } = useAuth();
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState("");
  const sentinel = useRef<HTMLDivElement>(null);
  const { setPageHeader } = usePageHeader();
  const [form, setForm] = useState<"receipt" | Payment | null>(null);
  const [saved, setSaved] = useState(false);
  const canView = hasPermission(user, business?.id, "payments") && hasPermission(user, business?.id, "clients");
  const canCreate = canView && hasPermission(user, business?.id, "payments", "create");
  useEffect(() => {
    const timer = window.setTimeout(() => { setQuery(search); }, 250);
    return () => window.clearTimeout(timer);
  }, [search]);
  const payments = useInfiniteQuery({
    queryKey: ["client-payments", "infinite", business?.id, client?.id, query, kind],
    initialPageParam: 1,
    queryFn: ({ pageParam }) => paymentsApi.list({ business: business!.id, client: client?.id, q: query, kind, page: pageParam }),
    getNextPageParam: (lastPage, _pages, pageParam) => lastPage.next ? pageParam + 1 : undefined,
    enabled: canView,
  });
  const { hasNextPage, isFetching, isError, fetchNextPage } = payments;
  useEffect(() => {
    setPageHeader({ title: t("payments.title") });
    return () => setPageHeader(null);
  }, [setPageHeader, t]);
  useEffect(() => {
    if (!sentinel.current || !hasNextPage || isFetching || isError) return;
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) void fetchNextPage();
    }, { rootMargin: "240px" });
    observer.observe(sentinel.current);
    return () => observer.disconnect();
  }, [hasNextPage, isFetching, isError, fetchNextPage]);
  return <>
    <section data-testid="payments-journal" aria-label={t("payments.title")} className="min-w-0 space-y-4">
      <h1 className="sr-only">{t("payments.title")}</h1>
      {client && <p className="break-words text-sm text-platforma-muted">{client.label}</p>}
      <div className="space-y-4">
        {!canView ? <ForbiddenState /> : <>
          <div data-testid="payments-toolbar" className="flex min-w-0 flex-wrap items-end gap-3 [&>*]:min-w-0">
            <div className="w-full sm:w-64"><Input label={t("payments.search")} value={search} maxLength={200} onChange={(e) => setSearch(e.target.value)} /></div>
            <div className="w-full sm:w-52"><Select label={t("payments.kind")} value={kind} onChange={(e) => { setKind(e.target.value); }} options={[
              { value: "", label: t("payments.all") }, { value: "receipt", label: t("payments.receipt") }, { value: "refund", label: t("payments.refundKind") },
            ]} /></div>
            {canCreate && <Button type="button" className="min-h-11" onClick={() => { setForm("receipt"); setSaved(false); }} data-testid="payment-add"><Plus aria-hidden size={18} />{t("payments.add")}</Button>}
          </div>
          {saved && <p role="status" className="text-sm text-platforma-success">{t("payments.saved")}</p>}
          {payments.isLoading && <LoadingState />}
          {payments.error && !payments.isFetchNextPageError && <ErrorState error={payments.error} message={getApiErrorMessage(payments.error)} action={<Button variant="secondary" onClick={() => void payments.refetch()}>{t("common.retry")}</Button>} />}
          {!payments.isFetching && !payments.error && payments.data?.pages[0]?.count === 0 && <EmptyState title={t("payments.empty")} description={t("payments.emptyText")} />}
          {payments.data && <ul className="space-y-3" aria-label={t("payments.title")}>
            {payments.data.pages.flatMap(page => page.results).map((payment) => <li key={payment.id} className="space-y-3 rounded-card border border-platforma-border bg-surface-card p-4" data-testid={`payment-row-${payment.id}`}>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0"><p className="break-words font-semibold">{payment.client_name}</p><p className="text-sm text-platforma-muted">#{payment.id} · {t(payment.kind === "refund" ? "payments.refundKind" : "payments.receipt")}{payment.original ? ` · #${payment.original}` : ""}</p></div>
                <strong className="break-all text-lg tabular-nums">{payment.kind === "refund" ? "−" : "+"}{payment.amount} {payment.currency}</strong>
              </div>
              <dl className="grid gap-2 text-sm sm:grid-cols-2">
                <div><dt className="text-platforma-muted">{t("payments.date")}</dt><dd>{formatDateTime(payment.occurred_at)}</dd></div>
                <div><dt className="text-platforma-muted">{t("payments.method")}</dt><dd>{t(`payments.method.${payment.method}`)}</dd></div>
                <div><dt className="text-platforma-muted">{t("payments.source")}</dt><dd>{t(payment.source === "manual" ? "payments.manual" : "payments.integration")}</dd></div>
                <div><dt className="text-platforma-muted">{t("payments.actor")}</dt><dd className="break-words">{payment.actor_name || "—"} · {formatDateTime(payment.created_at)}</dd></div>
                {payment.link && <div><dt className="text-platforma-muted">{t("payments.link")}</dt><dd>{t(`payments.${payment.link.kind}`)} #{payment.link.id}</dd></div>}
                {Number(payment.refunded_amount) > 0 && <div><dt className="text-platforma-muted">{t("payments.refunded")}</dt><dd>{payment.refunded_amount} {payment.currency}</dd></div>}
              </dl>
              {(payment.note || payment.reason) && <p className="whitespace-pre-wrap break-words text-sm">{payment.reason || payment.note}</p>}
              {payment.can_refund && <Button type="button" variant="secondary" onClick={() => { setForm(payment); setSaved(false); }}>{t("payments.refund")}</Button>}
            </li>)}
          </ul>}
          <div ref={sentinel} aria-hidden="true" className="h-px" />
          {payments.isFetchingNextPage && <LoadingState />}
          {payments.isFetchNextPageError && <ErrorState error={payments.error} action={<Button variant="secondary" onClick={() => void payments.fetchNextPage()}>{t("common.retry")}</Button>} />}
        </>}
      </div>
    </section>
    {form && business && <PaymentForm businessId={business.id} currency={business.currency} initialClient={client}
      original={form === "receipt" ? undefined : form} canLinkDeal={hasPermission(user, business.id, "deals")}
      canLinkAppointment={hasPermission(user, business.id, "appointments")} onClose={() => setForm(null)}
      onSaved={() => { setForm(null); setSaved(true); }} />}
  </>;
}

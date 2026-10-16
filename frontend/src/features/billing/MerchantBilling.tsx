import { useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { billingCommerceApi, type BillingBuyer } from "../../api/billingCommerce";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { hasPermission } from "../../lib/permissions";
import { useAuth } from "../auth/AuthProvider";
import { TaskDraftGuard } from "../tasks/components/TaskDraftGuard";
import { ClinicPager } from "../platform/ClinicReadUI";
import { BillingOrderCard } from "./BillingOrderCard";

export function MerchantBilling({ business }: { business: string }) {
  const { t } = useI18n(); const { user } = useAuth();
  const manage = hasPermission(user, Number(business), "billing", "manage");
  const [page, setPage] = useState(1); const [offer, setOffer] = useState("");
  const [buyer, setBuyer] = useState<BillingBuyer>({ kind: "company", name: "", email: "", tax_id: "" });
  const requestId = useRef(crypto.randomUUID());
  const query = useQuery({ queryKey: ["billing-orders", business, page], queryFn: () => billingCommerceApi.get(business, false, page), gcTime: 0, retry: false });
  const mutation = useMutation({ mutationFn: async (command: { action: "create" | "checkout" | "reconcile"; id?: string }) => {
    if (command.action === "create") return billingCommerceApi.create(business, { request_id: requestId.current, offer_id: offer, buyer });
    return billingCommerceApi.card(business, command.id!, command.action);
  }, retry: false, onSuccess: async (_, command) => {
    if (command.action === "create") { setOffer(""); setBuyer({ kind: "company", name: "", email: "", tax_id: "" }); requestId.current = crypto.randomUUID(); }
    await query.refetch();
  } });
  const dirty = Boolean(offer || buyer.name || buyer.email || buyer.tax_id);
  const changeBuyer = (values: Partial<BillingBuyer>) => { setBuyer(current => ({ ...current, ...values })); requestId.current = crypto.randomUUID(); };
  if (query.isLoading) return <LoadingState />;
  if (query.isError || !query.data) return <ErrorState error={query.error} action={<Button onClick={() => void query.refetch()}>{t("common.refresh")}</Button>} />;
  const data = query.data; const pending = mutation.isPending || query.isFetching;
  return <div className="space-y-4 p-4" data-testid="merchant-billing">
    {(dirty || pending) && <TaskDraftGuard dirty={dirty} pending={pending} />}
    <Button variant="secondary" disabled={pending} onClick={() => void query.refetch()}>{t("common.refresh")}</Button>
    {!data.enabled && <p role="status">{t("commerce.unavailable")}</p>}
    {data.enabled && !data.offers.length && <p role="status">{t("commerce.noOffers")}</p>}
    {data.enabled && manage && data.offers.length > 0 && <form className="grid gap-3 sm:grid-cols-2" data-testid="billing-create" onSubmit={event => { event.preventDefault(); mutation.mutate({ action: "create" }); }}>
      <Select label={t("commerce.offer")} value={offer} required disabled={pending} options={[{ value: "", label: t("commerce.select") }, ...data.offers.map(row => ({ value: row.id, label: `${row.plan} · ${row.amount} ${row.currency}` }))]} onChange={event => { setOffer(event.target.value); requestId.current = crypto.randomUUID(); }} />
      <Select label={t("commerce.buyerType")} value={buyer.kind} disabled={pending} options={["company", "sole_trader", "person"].map(value => ({ value, label: t(`commerce.buyer.${value}`) }))} onChange={event => changeBuyer({ kind: event.target.value as BillingBuyer["kind"] })} />
      <Input label={t("commerce.buyerName")} name="buyer_name" value={buyer.name} required maxLength={255} disabled={pending} onChange={event => changeBuyer({ name: event.target.value })} />
      <Input label={t("commerce.taxId")} name="tax_id" value={buyer.tax_id} required={buyer.kind !== "person"} maxLength={64} disabled={pending} onChange={event => changeBuyer({ tax_id: event.target.value })} />
      <Input label={t("commerce.email")} name="buyer_email" type="email" value={buyer.email} required disabled={pending} onChange={event => changeBuyer({ email: event.target.value })} />
      {offer && <p className="text-sm sm:col-span-2">{t("commerce.period")}: {data.offers.find(row => row.id === offer)?.period_start} — {data.offers.find(row => row.id === offer)?.period_end}</p>}
      <Button type="submit" disabled={!offer || pending}>{t("commerce.create")}</Button>
    </form>}
    {mutation.isError && <ErrorState error={mutation.error} />}
    {!data.orders.length && <p role="status">{t("commerce.empty")}</p>}
    {data.orders.map(order => <BillingOrderCard key={order.id} order={order}>
      {manage && data.enabled && <div className="flex flex-wrap gap-2">
        {data.card_available && order.payment_status === "awaiting" && !order.applied_at && <Button disabled={pending} onClick={() => mutation.mutate({ action: "checkout", id: order.id })}>{t("commerce.payCard")}</Button>}
        {order.attempts[0]?.checkout_url && <a className="platforma-focus-ring inline-flex min-h-10 items-center text-brand-700" href={order.attempts[0].checkout_url} target="_blank" rel="noopener noreferrer">{t("commerce.openCheckout")}</a>}
        {data.card_available && order.attempts.length > 0 && <Button variant="secondary" disabled={pending} onClick={() => mutation.mutate({ action: "reconcile", id: order.id })}>{t("commerce.checkPayment")}</Button>}
        {!data.card_available && <p className="text-sm" role="status">{t("commerce.cardUnavailable")}</p>}
      </div>}
    </BillingOrderCard>)}
    {data.count > 10 && <ClinicPager page={page} count={data.count} size={10} change={setPage} />}
  </div>;
}

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { visitPlansApi } from "../../api/visitPlans";
import { Button } from "../../components/ui/Button";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";

export function PlanTermsHistory({ business, plan }: { business: number; plan: number }) {
  const { t, language } = useI18n();
  const [open, setOpen] = useState(false);
  const [page, setPage] = useState(1);
  const history = useQuery({ queryKey: ["visit-plans", "terms-history", business, plan, page],
    queryFn: () => visitPlansApi.termsHistory(business, plan, page), enabled: open });
  return <details onToggle={event => setOpen(event.currentTarget.open)} className="border-t border-platforma-border pt-3">
    <summary className="platforma-focus-ring cursor-pointer rounded py-2 font-semibold">{t("planMoney.history")}</summary>
    {open && (history.isPending ? <LoadingState /> : history.error ? <ErrorState error={history.error} action={<Button onClick={() => void history.refetch()}>{t("common.retry")}</Button>} /> : <>
      <ol className="divide-y divide-platforma-border">{history.data?.results.map(row => <li key={row.id} className="space-y-1 py-3 text-sm">
        <p className="font-semibold">#{row.revision} · {t(row.mode === "package" ? "planMoney.package" : "planMoney.perVisit")} · {row.total} {row.currency}</p>
        <p>{new Date(row.created_at).toLocaleString(language)} · {row.actor_name}</p><p className="break-words">{row.reason}</p>
      </li>)}</ol>
      <div className="flex justify-between gap-2"><Button variant="secondary" disabled={!history.data?.previous} onClick={() => setPage(p => p - 1)}>{t("pagination.previous")}</Button><Button variant="secondary" disabled={!history.data?.next} onClick={() => setPage(p => p + 1)}>{t("pagination.next")}</Button></div>
    </>)}
  </details>;
}

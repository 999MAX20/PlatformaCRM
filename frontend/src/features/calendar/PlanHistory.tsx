import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { visitPlansApi } from "../../api/visitPlans";
import { Button } from "../../components/ui/Button";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/StateViews";
import { formatDateTime } from "../../lib/format";
import { useI18n } from "../../lib/i18n";

export function PlanHistory({ business, actor, plan, timeZone }: { business: number; actor: number; plan: number; timeZone: string }) {
  const { t, language } = useI18n();
  const [page, setPage] = useState(1);
  const query = useQuery({ queryKey: ["visit-plans", "history", business, actor, plan, page], queryFn: () => visitPlansApi.history(business, plan, page) });
  const locale = language === "kk" ? "kk-KZ" : language === "en" ? "en-US" : "ru-RU";
  return <section className="space-y-3" aria-label={t("nav.timeline")}>
    <h2 className="font-semibold">{t("nav.timeline")}</h2>
    {query.isPending ? <LoadingState /> : query.error ? <ErrorState action={<Button onClick={() => void query.refetch()}>{t("common.retry")}</Button>} /> : query.data?.results.length ? <>
      <ul className="divide-y divide-platforma-border">{query.data.results.map(event => <li key={event.id} className="flex flex-wrap justify-between gap-2 py-2 text-sm"><span>{t(`plans.command.${event.command}`)}{event.actor_name ? ` · ${event.actor_name}` : ""}</span><time dateTime={event.created_at}>{formatDateTime(event.created_at, timeZone, false, locale)}</time></li>)}</ul>
      {query.data.previous || query.data.next ? <div className="flex justify-between"><Button variant="secondary" disabled={!query.data.previous} onClick={() => setPage(value => value - 1)}>{t("pagination.previous")}</Button><Button variant="secondary" disabled={!query.data.next} onClick={() => setPage(value => value + 1)}>{t("pagination.next")}</Button></div> : null}
    </> : <EmptyState title={t("tasks.noHistory")} />}
  </section>;
}

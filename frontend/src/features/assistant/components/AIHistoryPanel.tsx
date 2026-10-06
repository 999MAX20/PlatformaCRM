import { LoadingState } from "../../../components/ui/StateViews";
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { aiCRMApi, type CRMEntity } from "../../../api/aiCRM";
import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { Card, CardBody } from "../../../components/ui/Card";
import { Input } from "../../../components/ui/Input";
import { Textarea } from "../../../components/ui/Textarea";
import { formatMoney } from "../../../lib/format";
import { useI18n } from "../../../lib/i18n";
import { FinancialStatus } from "../../analytics/FinancialSummary";
import type { Id } from "../../../types";

export function AIHistoryPanel({ businessId, agentId, conversationMode = false }: { businessId: Id; agentId?: Id; conversationMode?: boolean }) {
  const { t } = useI18n();
  const today = new Date().toLocaleDateString("en-CA");
  const [start, setStart] = useState(`${today.slice(0, 7)}-01`);
  const [end, setEnd] = useState(today);
  const [period, setPeriod] = useState({ start, end });
  const [question, setQuestion] = useState("");
  const history = useQuery({ queryKey: ["ai-history", businessId, agentId, period], queryFn: () => aiCRMApi.history({ business: businessId, agent: agentId, ...period }) });
  const explain = useMutation({ mutationFn: () => aiCRMApi.explainHistory({ business: businessId, agent: agentId, ...period, question }) });
  const report = history.data;
  const money = (value: string | null | undefined) => value == null ? "—" : formatMoney(value, report?.financial.currency);
  return <Card aria-label={t("aiHistory.title")}><CardBody className="space-y-4">
    <h2 className="text-lg font-semibold">{t("aiHistory.title")}</h2>
    <form className="grid items-end gap-3 sm:grid-cols-[1fr_1fr_auto]" onSubmit={event => { event.preventDefault(); explain.reset(); setPeriod({ start, end }); }}>
      <Input type="date" required label={t("aiHistory.start")} value={start} max={end} onChange={event => setStart(event.target.value)} />
      <Input type="date" required label={t("aiHistory.end")} value={end} min={start} onChange={event => setEnd(event.target.value)} />
      <Button type="submit" disabled={!start || !end || start > end} isLoading={history.isFetching}>{t("aiHistory.show")}</Button>
    </form>
    {history.isLoading && <LoadingState />}
    {history.error && <div role="alert"><p>{getApiErrorMessage(history.error)}</p><Button variant="secondary" onClick={() => history.refetch()}>{t("aiCRM.retry")}</Button></div>}
    {report && <>
      <p className="text-sm text-platforma-subtle">{t("aiHistory.comparisonPeriod", { start: report.previous_period.start, end: report.previous_period.end })} · {report.timezone}</p>
      <FinancialStatus report={report.financial} />
      {report.financial.coverage === "recorded_manual_operations" && <p className="text-sm text-platforma-subtle">{t("aiHistory.manualCoverage", { count: report.financial.operation_count || 0 })}</p>}
      <div className="overflow-x-auto" tabIndex={0}><table className="w-full text-left text-sm" aria-label={t("aiHistory.cashTable")}>
        <thead><tr><th className="p-2">{t("aiHistory.metric")}</th><th className="p-2">{t("aiHistory.current")}</th><th className="p-2">{t("aiHistory.previous")}</th><th className="p-2">{t("aiHistory.change")}</th></tr></thead>
        <tbody>{(["receipts", "refunds", "net_receipts"] as const).map(key => <tr key={key} className="border-t border-platforma-border"><th className="p-2 font-medium">{t(`finance.${key}`)}</th><td className="p-2 tabular-nums">{money(report.financial[key])}</td><td className="p-2 tabular-nums">{money(report.previous_financial[key])}</td><td className="p-2 tabular-nums">{money(report.financial_change[key].absolute)}{report.financial_change[key].percent !== null ? ` (${report.financial_change[key].percent}%)` : ""}</td></tr>)}</tbody>
      </table></div>
      <p className="text-sm text-platforma-subtle">{t("aiHistory.noProfitDebt")}</p>
      {report.previous_financial.state === "stale" && <FinancialStatus report={report.previous_financial} />}
      <div className="overflow-x-auto" tabIndex={0}><table className="w-full text-left text-sm" aria-label={t("aiHistory.crmTable")}>
        <caption className="mb-2 text-left text-sm text-platforma-subtle">{t("aiHistory.historyCoverage")}</caption>
        <thead><tr><th className="p-2">{t("aiCRM.entity")}</th><th className="p-2">{t("aiHistory.current")}</th><th className="p-2">{t("aiHistory.previous")}</th><th className="p-2">{t("aiHistory.change")}</th></tr></thead>
        <tbody>{(Object.entries(report.operations) as Array<[CRMEntity, NonNullable<typeof report.operations[CRMEntity]>]>).map(([entity, metric]) => <tr key={entity} className="border-t border-platforma-border"><th className="p-2 font-medium">{t(`aiWorkflow.source.${entity}`)}</th><td className="p-2 tabular-nums">{metric.count}</td><td className="p-2 tabular-nums">{metric.previous_count}</td><td className="p-2 tabular-nums">{metric.difference > 0 ? "+" : ""}{metric.difference}</td></tr>)}</tbody>
      </table></div>
      {report.series.points.length > 0 && <details><summary className="cursor-pointer py-2 font-medium">{t("aiHistory.cashSeries")}</summary><div className="max-h-80 overflow-auto" tabIndex={0}><table className="w-full text-left text-sm"><thead><tr><th className="p-2">{t("aiHistory.period")}</th><th className="p-2">{t("finance.receipts")}</th><th className="p-2">{t("finance.refunds")}</th><th className="p-2">{t("finance.net_receipts")}</th></tr></thead><tbody>{report.series.points.map(point => <tr key={point.period}><th className="p-2 font-medium">{point.period}</th><td className="p-2">{money(point.receipts)}</td><td className="p-2">{money(point.refunds)}</td><td className="p-2">{money(point.net_receipts)}</td></tr>)}</tbody></table></div><p className="text-xs text-platforma-subtle">{t("aiHistory.zeroBuckets")}</p></details>}
      {report.state === "no_data" && <p role="status">{t("finance.unavailable")}</p>}
      {!conversationMode && <form className="space-y-3" onSubmit={event => { event.preventDefault(); explain.mutate(); }}>
        <Textarea label={t("aiHistory.question")} value={question} disabled={explain.isPending} onChange={event => { setQuestion(event.target.value); explain.reset(); }} />
        <Button type="submit" variant="ai" disabled={!question.trim() || report.state === "no_data" || start !== period.start || end !== period.end} isLoading={explain.isPending}>{t("aiHistory.explain")}</Button>
      </form>}
      {explain.error && <p role="alert" className="text-platforma-danger">{getApiErrorMessage(explain.error)}</p>}
      {explain.data && <div role="status" className="space-y-2 whitespace-pre-wrap text-sm"><p>{explain.data.answer || t("finance.unavailable")}</p>{explain.data.provider_state === "mock" && <p>{t("aiQuality.mock")}</p>}{explain.data.sources.length > 0 && <p className="text-platforma-subtle">{t("aiHistory.answerSource", period)}</p>}</div>}
    </>}
  </CardBody></Card>;
}

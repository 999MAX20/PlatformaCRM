import { useMemo } from "react";

import type { Id, Lead } from "../../../types";
import type { LeadAiInsight, LeadFilter, Translate } from "../types";

type LeadSummary = {
  total?: number;
  new?: number;
  in_progress?: number;
  hot?: number;
  unanswered?: number;
  attention?: number;
  mine?: number;
};

export function useLeadsWorkspaceDisplay({
  t,
  leadSummary,
  totalLeadCount,
  allLeads,
  aiInsights,
  userId,
  pageRows,
  safePage,
  pageSize,
  pageCount,
}: {
  t: Translate;
  leadSummary?: LeadSummary;
  totalLeadCount: number;
  allLeads: Lead[];
  aiInsights: Map<Id, LeadAiInsight>;
  userId?: Id;
  pageRows: Lead[];
  safePage: number;
  pageSize: number;
  pageCount: number;
}) {
  const filters = useMemo(() => [
    { value: "all" as LeadFilter, label: t("leads.filterAll"), count: leadSummary?.total },
    { value: "new" as LeadFilter, label: t("leads.filterNew"), count: leadSummary?.new },
    { value: "in_progress" as LeadFilter, label: t("leads.statusInProgress"), count: leadSummary?.in_progress },
    { value: "attention" as LeadFilter, label: t("leads.filterAttention"), count: leadSummary?.attention },
  ], [leadSummary, t]);

  const pageStart = pageRows.length ? (safePage - 1) * pageSize + 1 : 0;
  const pageEnd = pageRows.length ? pageStart + pageRows.length - 1 : 0;
  const visiblePages = Array.from({ length: pageCount })
    .map((_, index) => index + 1)
    .filter((itemPage) => pageCount <= 5 || itemPage === 1 || itemPage === pageCount || Math.abs(itemPage - safePage) <= 1)
    .slice(0, 7);

  return { filters, pageStart, pageEnd, visiblePages };
}

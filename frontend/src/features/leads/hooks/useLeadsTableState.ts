import { useCrmFilters } from "../../../components/crm/useCrmFilters";
import { useCallback, useEffect, useState } from "react";

import {
  defaultVisibleColumns,
  LEAD_COLUMNS_KEY,
  LEAD_COLUMN_ORDER_KEY,
  leadColumnOrder,
  LEADS_PAGE_SIZE,
  type LeadColumnKey,
  type LeadFilter,
  type Translate,
} from "../types";
import { loadJson, saveJson } from "../utils/leadStorage";

export function useLeadsTableState({
  searchParams,
  t,
  onNotice,
}: {
  searchParams: URLSearchParams;
  t: Translate;
  onNotice: (message: string | null, tone?: "success" | "info" | "warning" | "danger") => void;
}) {
  const { state, update } = useCrmFilters("leads");
  const filter = state.quick as LeadFilter;
  const { source, search } = state;
  const setFilter = (quick: LeadFilter) => update({ quick });
  const setSource = (source: string) => update({ source });
  const setSearch = (search: string) => update({ search }, true);
  const [sortByAi, setSortByAi] = useState(true);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(LEADS_PAGE_SIZE);
  const [moreMenuOpen, setMoreMenuOpen] = useState(false);
  const [visibleColumns, setVisibleColumns] = useState<Record<LeadColumnKey, boolean>>(() => {
    const saved = loadJson<Partial<Record<LeadColumnKey, boolean>>>(LEAD_COLUMNS_KEY, {});
    const next = { ...defaultVisibleColumns, ...saved };
    return { ...next, lead: true };
  });
  const [columnOrder, setColumnOrder] = useState<LeadColumnKey[]>(() => {
    const saved = loadJson<LeadColumnKey[]>(LEAD_COLUMN_ORDER_KEY, leadColumnOrder);
    return [...saved.filter((column): column is LeadColumnKey => leadColumnOrder.includes(column)), ...leadColumnOrder.filter((column) => !saved.includes(column))];
  });

  useEffect(() => {
    setPage(1);
  }, [JSON.stringify(state)]);


  useEffect(() => {
    saveJson(LEAD_COLUMNS_KEY, visibleColumns);
  }, [visibleColumns]);

  useEffect(() => {
    saveJson(LEAD_COLUMN_ORDER_KEY, columnOrder);
  }, [columnOrder]);

  const shareView = useCallback(async () => {
    const url = `${window.location.origin}${window.location.pathname}?${searchParams.toString()}`;
    await navigator.clipboard?.writeText(url);
    onNotice(t("leads.viewCopied"));
  }, [onNotice, searchParams, t]);

  return {
    filter,
    setFilter,
    source,
    setSource,
    search,
    setSearch,
    sortByAi,
    setSortByAi,
    page,
    setPage,
    pageSize,
    setPageSize,
    moreMenuOpen,
    setMoreMenuOpen,
    visibleColumns,
    setVisibleColumns,
    columnOrder,
    shareView,
  };
}

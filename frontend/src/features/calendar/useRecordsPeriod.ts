import { useCallback, useLayoutEffect, useState } from "react";
import { createSearchParams, useSearchParams, type SetURLSearchParams } from "react-router";
import { savedRecordPeriod } from "./recordFilters";

export function useRecordsPeriod(businessId?: number, userId?: number) {
  const [params, setParams] = useSearchParams();
  const key = businessId && userId ? `records-period:${userId}:${businessId}` : "";
  const [readyKey, setReadyKey] = useState("");
  const persist = useCallback((next: URLSearchParams) => {
    if (!key) return;
    try {
      const period = savedRecordPeriod(next.toString());
      if (period) sessionStorage.setItem(key, period.toString());
      else if (!next.has("client") && !next.has("attention") && !next.has("create")) sessionStorage.removeItem(key);
    } catch { /* URL filters remain usable without browser storage. */ }
  }, [key]);
  const updateParams: SetURLSearchParams = useCallback((nextInit, options) => {
    const next = createSearchParams(typeof nextInit === "function" ? nextInit(params) : nextInit);
    persist(next);
    setParams(next, options);
  }, [params, persist, setParams]);
  let restoring = false;
  try { restoring = !!key && !params.size && !!savedRecordPeriod(sessionStorage.getItem(key)); } catch { /* Storage is optional. */ }
  useLayoutEffect(() => {
    if (!key) return;
    try {
      if (!params.size) {
        const saved = savedRecordPeriod(sessionStorage.getItem(key));
        if (saved) { setParams(saved, { replace: true }); setReadyKey(key); return; }
      }
      persist(params);
    } catch { /* URL filters remain the source of truth without browser storage. */ }
    setReadyKey(key);
  }, [key, params, persist, setParams]);
  return { params, setParams: updateParams, periodReady: !!key && readyKey === key && !restoring };
}

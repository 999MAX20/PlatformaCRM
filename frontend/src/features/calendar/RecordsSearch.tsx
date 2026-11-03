import { Search } from "lucide-react";
import { useEffect, useState } from "react";
import { useLocation, type SetURLSearchParams } from "react-router";
import { useI18n } from "../../lib/i18n";
import { patchRecordFilters } from "./recordFilters";

export function RecordsSearch({ params, setParams }: { params: URLSearchParams; setParams: SetURLSearchParams }) {
  const { t } = useI18n();
  const location = useLocation();
  const query = params.get("search") || "";
  const [draft, setDraft] = useState(query);
  useEffect(() => { setDraft(query); }, [query, location.key]);
  useEffect(() => {
    if (draft === query) return;
    const timer = window.setTimeout(() => setParams(current => patchRecordFilters(current, { search: draft }), { replace: true }), 300);
    return () => window.clearTimeout(timer);
  }, [draft, query, location.key, setParams]);
  return <label className="relative w-60 min-w-48 flex-1">
    <Search size={17} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-platforma-muted" />
    <input aria-label={t("records.search")} placeholder={t("records.search")} value={draft} onChange={event => setDraft(event.target.value)} className="platforma-focus-ring h-11 w-full rounded-control border border-platforma-control bg-platforma-card pl-9 pr-3 text-sm text-platforma-text placeholder:text-platforma-muted lg:h-10" />
  </label>;
}

import { useCallback, useEffect, useRef, useState } from "react";
import { medicalTemplatesApi, type TemplateRow } from "../../../api/medicalTemplates";
import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import { medicalRoleDenied } from "../roles/useMedicalRolePage";

type Selected = { id: number; title: string };
export function DocumentRuleTemplates({ businessId, selected, onChange, onDenied }: {
  businessId: number; selected: Selected[]; onChange: (value: Selected[]) => void; onDenied: (cause: unknown) => void;
}) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [rows, setRows] = useState<TemplateRow[]>([]);
  const [next, setNext] = useState<number | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const request = useRef<AbortController | null>(null);
  const load = useCallback(async (before?: number) => {
    request.current?.abort(); const controller = new AbortController(); request.current = controller;
    setLoading(true); setError(null); if (!before) { setRows([]); setNext(null); }
    try {
      const page = await medicalTemplatesApi.managed(businessId, before, controller.signal, { q: search });
      if (!controller.signal.aborted) { setRows(previous => before ? [...previous, ...page.results] : page.results); setNext(page.next_before_id); }
    } catch (cause) { if (!controller.signal.aborted) { if (medicalRoleDenied(cause)) onDenied(cause); else setError(cause); } }
    finally { if (!controller.signal.aborted) setLoading(false); }
  }, [businessId, search, onDenied]);
  useEffect(() => { if (open) void load(); return () => request.current?.abort(); }, [open, load]);
  function find() { if (search === query) void load(); else setSearch(query); }
  return <section className="space-y-3" data-testid="rule-templates">
    <h3 className="text-base font-semibold">{t("medical.rules.templates")}</h3>
    <ul className="space-y-2">{selected.map(item => <li key={item.id} className="flex items-center justify-between gap-3">
      <span className="min-w-0 break-words text-sm">{item.title}</span><Button type="button" size="lg" variant="secondary"
        aria-label={`${t("medical.templates.removeService")}: ${item.title}`} onClick={() => onChange(selected.filter(row => row.id !== item.id))}>{t("medical.templates.removeService")}</Button>
    </li>)}</ul>
    <Button type="button" size="lg" variant="secondary" aria-expanded={open} onClick={() => setOpen(value => !value)}>{t("medical.rules.selectTemplates")}</Button>
    {open ? <div className="space-y-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end"><div className="min-w-0 flex-1"><Input label={t("medical.rules.searchTemplates")}
        value={query} maxLength={255} onChange={event => setQuery(event.target.value)} onKeyDown={event => { if (event.key === "Enter") { event.preventDefault(); find(); } }} /></div>
        <Button type="button" size="lg" variant="secondary" disabled={loading} onClick={find}>{t("common.search")}</Button></div>
      {error ? <ErrorState message={getApiErrorMessage(error)} action={<Button type="button" size="lg" onClick={() => void load()}>{t("common.retry")}</Button>} /> : null}
      <ul className="space-y-2">{rows.map(row => { const chosen = selected.some(item => item.id === row.template_id); return <li key={row.template_id}>
        <Button type="button" size="lg" variant="secondary" className="w-full justify-start text-left" aria-pressed={chosen}
          disabled={loading || (!chosen && selected.length >= 100)} onClick={() => onChange(chosen ? selected.filter(item => item.id !== row.template_id) : [...selected, { id: row.template_id, title: row.title }])}>
          {row.title}</Button></li>; })}</ul>
      {loading ? <LoadingState /> : !error && !rows.length ? <p className="text-sm">{t("medical.templates.noMatches")}</p> : null}
      {next && !error ? <Button type="button" size="lg" variant="secondary" disabled={loading} onClick={() => void load(next)}>{t("medical.templates.more")}</Button> : null}
    </div> : null}
  </section>;
}

import { useCallback, useEffect, useRef, useState } from "react";
import { medicalTemplatesApi, type TemplateService } from "../../../api/medicalTemplates";
import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import { medicalRoleDenied } from "../roles/useMedicalRolePage";

export function TemplateServices({ businessId, selected, onChange, onDenied }: {
  businessId: number; selected: TemplateService[]; onChange: (services: TemplateService[]) => void; onDenied: (cause: unknown) => void;
}) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const toggle = useRef<HTMLButtonElement>(null);
  return <div className="space-y-2" data-testid="template-services">
    <p className="text-sm font-medium">{t("medical.templates.servicesCount", { count: selected.length })}</p>
    {selected.map(service => <div key={service.id} className="flex items-center justify-between gap-2">
      <span className="min-w-0 break-words text-sm">{service.name}</span>
      <Button type="button" variant="secondary" aria-label={`${t("medical.templates.removeService")}: ${service.name}`}
        onClick={() => { onChange(selected.filter(item => item.id !== service.id)); toggle.current?.focus(); }}>{t("medical.templates.removeService")}</Button>
    </div>)}
    <Button ref={toggle} type="button" variant="secondary" aria-expanded={open} onClick={() => setOpen(value => !value)}>{t("medical.templates.selectServices")}</Button>
    {open ? <ServiceOptions businessId={businessId} selected={selected} onChange={onChange} onDenied={onDenied} /> : null}
  </div>;
}

function ServiceOptions({ businessId, selected, onChange, onDenied }: {
  businessId: number; selected: TemplateService[]; onChange: (services: TemplateService[]) => void; onDenied: (cause: unknown) => void;
}) {
  const { t } = useI18n();
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [rows, setRows] = useState<TemplateService[]>([]);
  const [cursor, setCursor] = useState<number | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const request = useRef<AbortController | null>(null);
  const retry = useRef<number | undefined>(undefined);
  const load = useCallback(async (before?: number) => {
    request.current?.abort(); const controller = new AbortController(); request.current = controller;
    retry.current = before; setLoading(true); setError(null);
    if (!before) { setRows([]); setCursor(null); }
    try {
      const page = await medicalTemplatesApi.services(businessId, search, before, controller.signal);
      if (!controller.signal.aborted) {
        setRows(previous => before ? [...previous, ...page.results.filter(item => !previous.some(row => row.id === item.id))] : page.results);
        setCursor(page.next_before_id);
      }
    } catch (cause) { if (!controller.signal.aborted) { if (medicalRoleDenied(cause)) onDenied(cause); else setError(cause); } }
    finally { if (!controller.signal.aborted) setLoading(false); }
  }, [businessId, search, onDenied]);
  useEffect(() => { void load(); return () => request.current?.abort(); }, [load]);
  function find() { if (query === search) void load(); else setSearch(query); }
  return <div className="space-y-2">
    <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
      <div className="min-w-0 flex-1"><Input label={t("medical.templates.searchServices")} value={query} maxLength={255}
        onChange={event => setQuery(event.target.value)} onKeyDown={event => { if (event.key === "Enter") { event.preventDefault(); find(); } }} /></div>
      <Button type="button" variant="secondary" disabled={loading} onClick={find}>{t("common.search")}</Button>
    </div>
    {error ? <ErrorState message={getApiErrorMessage(error)} action={<Button type="button" variant="secondary" onClick={() => void load(retry.current)}>{t("common.retry")}</Button>} /> : null}
    {rows.map(service => {
      const chosen = selected.some(item => item.id === service.id);
      return <Button key={service.id} type="button" variant="secondary" className="w-full justify-start whitespace-normal break-words text-left"
        aria-pressed={chosen} disabled={loading || (!chosen && selected.length >= 50)}
        onClick={() => onChange(chosen ? selected.filter(item => item.id !== service.id) : [...selected, service])}>
        <span className="min-w-0 break-words">{service.name}</span></Button>;
    })}
    {loading ? <LoadingState /> : !error && !rows.length ? <p role="status" className="text-sm text-platforma-subtle">{t("common.noResults")}</p> : null}
    {cursor && !error ? <Button type="button" variant="secondary" disabled={loading} onClick={() => void load(cursor)}>{t("medical.templates.more")}</Button> : null}
  </div>;
}

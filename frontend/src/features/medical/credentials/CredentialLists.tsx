import { useCallback, useEffect, useRef, useState } from "react";
import { medicalCredentialsApi as api, type CredentialSummary } from "../../../api/medicalCredentials";
import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { Select } from "../../../components/ui/Select";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import { medicalRoleDenied } from "../roles/useMedicalRolePage";

function usePage<T>(fetchPage: (before: number | undefined, signal: AbortSignal) => Promise<{ rows: T[]; cursor: number | null }>, onDenied: (cause: unknown) => void) {
  const [rows, setRows] = useState<T[]>([]);
  const [cursor, setCursor] = useState<number | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const request = useRef<AbortController | null>(null);
  const load = useCallback(async (before?: number) => {
    request.current?.abort(); const controller = new AbortController(); request.current = controller;
    setLoading(true); setError(null);
    try {
      const result = await fetchPage(before, controller.signal);
      if (!controller.signal.aborted) { setRows(previous => before ? [...previous, ...result.rows] : result.rows); setCursor(result.cursor); }
    } catch (cause) { if (!controller.signal.aborted) { if (medicalRoleDenied(cause)) onDenied(cause); else setError(cause); } }
    finally { if (!controller.signal.aborted) setLoading(false); }
  }, [fetchPage, onDenied]);
  useEffect(() => { void load(); return () => request.current?.abort(); }, [load]);
  return { rows, cursor, error, loading, load };
}

function PageState({ page }: { page: ReturnType<typeof usePage> }) {
  const { t } = useI18n();
  return <>{page.loading ? <LoadingState /> : null}
    {page.error ? <ErrorState message={getApiErrorMessage(page.error)} action={<Button onClick={() => void page.load(page.cursor ?? undefined)}>{t("common.retry")}</Button>} /> : null}
    {page.cursor && !page.error ? <Button variant="secondary" disabled={page.loading} onClick={() => void page.load(page.cursor!)}>{t("medical.templates.more")}</Button> : null}</>;
}

export function CredentialMembers({ businessId, value, onChange, onDenied }: {
  businessId: number; value: number | null; onChange: (value: number | null) => void; onDenied: (cause: unknown) => void;
}) {
  const { t } = useI18n();
  const fetchPage = useCallback(async (before: number | undefined, signal: AbortSignal) => {
    const page = await api.members(businessId, before, signal); return { rows: page.results, cursor: page.next_before_id };
  }, [businessId]);
  const page = usePage(fetchPage, onDenied);
  return <div className="space-y-2">
    <Select label={t("medical.credentials.profile")} value={value ?? "clinic"} onChange={event => onChange(event.target.value === "clinic" ? null : Number(event.target.value))}
      options={[{ value: "clinic", label: t("medical.credentials.clinic") }, ...page.rows.map(row => ({ value: row.id, label: row.name }))]} />
    <PageState page={page} />
  </div>;
}

export function CredentialHistory({ businessId, memberId, onSelect, onDenied }: {
  businessId: number; memberId: number | null; onSelect: (id: number) => void; onDenied: (cause: unknown) => void;
}) {
  const { t } = useI18n();
  const fetchPage = useCallback(async (before: number | undefined, signal: AbortSignal) => {
    const page = await api.history(businessId, memberId, before, signal); return { rows: page.results, cursor: page.next_before_revision };
  }, [businessId, memberId]);
  const page = usePage<CredentialSummary>(fetchPage, onDenied);
  return <section className="space-y-2" aria-label={t("medical.templates.history")}>
    <h3 className="text-base font-semibold">{t("medical.templates.history")}</h3>
    <div className="flex flex-wrap gap-2">{page.rows.map(row => <Button key={row.id} variant="secondary" onClick={() => onSelect(row.id)}>
      {t("medical.templates.version", { revision: row.revision })}</Button>)}</div>
    <PageState page={page} />
  </section>;
}

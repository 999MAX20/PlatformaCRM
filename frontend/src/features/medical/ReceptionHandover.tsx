import { useEffect, useRef, useState } from "react";
import axios from "axios";
import { medicalReceptionApi as api, type FollowUpOption, type ReceptionRequest } from "../../api/medicalReception";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { Textarea } from "../../components/ui/Textarea";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { ReceptionHistory } from "./ReceptionHistory";

export function ReceptionHandover({ businessId, row, timeZone, onDirty, onPending, onDenied, onDone }: {
  businessId: number; row: ReceptionRequest; timeZone: string; onDirty: (value: boolean) => void;
  onPending: (value: boolean) => void; onDenied: (cause: unknown) => void; onDone: () => void;
}) {
  const { t } = useI18n();
  const [target, setTarget] = useState<FollowUpOption | "queue" | null>(null);
  const [reason, setReason] = useState("");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<{ results: FollowUpOption[]; next_offset: number | null } | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [loading, setLoading] = useState(false);
  const [pending, setPending] = useState(false);
  const [catalogError, setCatalogError] = useState<unknown>(null);
  const [error, setError] = useState<unknown>(null);
  const [conflict, setConflict] = useState(false);
  const title = useRef<HTMLHeadingElement>(null);
  const command = useRef(new AbortController());
  const inFlight = useRef(false);
  const retry = useRef<{ fingerprint: string; key: string } | null>(null);
  useEffect(() => { title.current?.focus(); const controller = new AbortController(); command.current = controller; return () => controller.abort(); }, []);
  useEffect(() => {
    if (!row.actions.transfer) return;
    const controller = new AbortController(); setLoading(true); setCatalogError(null); setPage(null);
    const timer = window.setTimeout(() => {
      api.recipients(row.id, { business_id: businessId, search, offset }, controller.signal).then(result => {
        if (!controller.signal.aborted) setPage(result);
      }).catch(cause => {
        if (!controller.signal.aborted) {
          if (axios.isAxiosError(cause) && [401, 403, 404].includes(cause.response?.status ?? 0)) onDenied(cause);
          else setCatalogError(cause);
        }
      }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    }, search ? 250 : 0);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [businessId, row.id, row.actions.transfer, search, offset, attempt, onDenied]);
  const choices = page?.results ?? [];
  const selected = target && target !== "queue" ? target : null;
  const options = selected && !choices.some(item => item.id === selected.id) ? [selected, ...choices] : choices;
  async function submit() {
    if (!target || !reason.trim() || inFlight.current || conflict) return;
    if (!window.confirm(t("medical.reception.confirmTransfer"))) return;
    const payload = { business_id: businessId, expected_revision: row.revision,
      assignee_id: target === "queue" ? null : target.id, reason: reason.trim() };
    const fingerprint = JSON.stringify(payload);
    if (retry.current?.fingerprint !== fingerprint) retry.current = { fingerprint, key: crypto.randomUUID() };
    const controller = command.current;
    inFlight.current = true; setPending(true); onPending(true); setError(null);
    try {
      await api.transfer(row.id, payload, retry.current.key, controller.signal);
      if (!controller.signal.aborted) { onDirty(false); onDone(); }
    } catch (cause) {
      if (!controller.signal.aborted) {
        if (axios.isAxiosError(cause) && [401, 403, 404].includes(cause.response?.status ?? 0)) onDenied(cause);
        else { setError(cause); setConflict(axios.isAxiosError(cause) && cause.response?.status === 409); }
      }
    } finally { inFlight.current = false; onPending(false); if (!controller.signal.aborted) setPending(false); }
  }
  return <section className="min-w-0 space-y-4" data-testid="reception-handover">
    <h2 ref={title} tabIndex={-1} className="text-lg font-semibold">{t("medical.reception.handover")}</h2>
    <p className="break-words">{row.client_name} · {row.service_name}</p>
    {error ? <ErrorState message={conflict ? t("medical.clinical.conflict") : getApiErrorMessage(error)} /> : null}
    {conflict ? <Button size="lg" variant="secondary" onClick={() => {
      if (window.confirm(t("medical.clinical.discard"))) { onDirty(false); onDone(); }
    }}>{t("medical.clinical.reload")}</Button> : row.actions.transfer ? <form className="space-y-4" onSubmit={event => { event.preventDefault(); void submit(); }}>
      <Input label={t("medical.reception.searchRecipient")} value={search} maxLength={120} disabled={pending}
        onChange={event => { setSearch(event.target.value); setOffset(0); }} />
      <Select label={t("medical.reception.recipient")} value={target === "queue" ? "queue" : target?.id ?? ""} disabled={pending || loading || !!catalogError}
        options={[{ value: "", label: t("common.select") }, { value: "queue", label: t("medical.reception.release") }, ...options.map(item => ({ value: item.id, label: item.name }))]}
        onChange={event => { const value = event.target.value; setTarget(value === "queue" ? "queue" : options.find(item => item.id === Number(value)) ?? null); onDirty(true); }} />
      {loading ? <LoadingState /> : null}
      {catalogError ? <ErrorState message={getApiErrorMessage(catalogError)} action={<Button type="button" size="lg" variant="secondary" onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button>} /> : null}
      <div className="flex flex-wrap gap-2">
        {offset > 0 ? <Button type="button" size="lg" variant="secondary" disabled={pending || loading} onClick={() => setOffset(Math.max(0, offset - 25))}>{t("medical.reception.previous")}</Button> : null}
        {page?.next_offset != null ? <Button type="button" size="lg" variant="secondary" disabled={pending || loading} onClick={() => setOffset(page.next_offset!)}>{t("medical.reception.next")}</Button> : null}
      </div>
      <Textarea label={t("medical.reception.transferReason")} required maxLength={1000} value={reason} disabled={pending}
        onChange={event => { setReason(event.target.value); onDirty(true); }} />
      <Button type="submit" size="lg" disabled={!target || !reason.trim() || loading || !!catalogError} isLoading={pending}>{t("medical.reception.transfer")}</Button>
    </form> : null}
    <ReceptionHistory businessId={businessId} requestId={row.id} timeZone={timeZone} onDenied={onDenied} />
  </section>;
}

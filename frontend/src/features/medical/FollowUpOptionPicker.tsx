import { useEffect, useState } from "react";
import axios from "axios";
import { medicalReceptionApi, type FollowUpOption, type FollowUpOptions, type FollowUpScope } from "../../api/medicalReception";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";

export function FollowUpOptionPicker({ scope, kind, value, onChange, onDenied, disabled }: {
  scope: FollowUpScope; kind: "service" | "staff"; value: FollowUpOption | null;
  onChange: (value: FollowUpOption, userChanged: boolean) => void; onDenied: (cause: unknown) => void; disabled: boolean;
}) {
  const { t } = useI18n();
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [attempt, setAttempt] = useState(0);
  const [page, setPage] = useState<FollowUpOptions | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(null); setPage(null);
    const timer = window.setTimeout(() => {
      medicalReceptionApi.catalog({ ...scope, kind, search, offset }, controller.signal)
        .then(result => {
          if (!controller.signal.aborted) {
            setPage(result);
            if (!value && !search && offset === 0 && result.default) onChange(result.default, false);
          }
        }).catch(cause => {
          if (!controller.signal.aborted) {
            if (axios.isAxiosError(cause) && [401, 403, 404].includes(cause.response?.status ?? 0)) onDenied(cause);
            else setError(cause);
          }
        }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    }, search ? 250 : 0);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [scope.business_id, scope.patient_id, scope.encounter_id, scope.participation_id, kind, search, offset, attempt]);
  const options = page?.results ?? [];
  const choices = value && !options.some(item => item.id === value.id) ? [value, ...options] : options;
  return <div className="min-w-0 space-y-2">
    <Input label={t(`medical.reception.search.${kind}`)} value={search} disabled={disabled} maxLength={120}
      onChange={event => { setSearch(event.target.value); setOffset(0); }} />
    <Select label={t(`medical.reception.${kind}`)} value={value?.id ?? ""} disabled={disabled || loading || !!error}
      options={[{ value: "", label: t("common.select") }, ...choices.map(item => ({ value: item.id, label: item.name }))]}
      onChange={event => { const selected = choices.find(item => item.id === Number(event.target.value)); if (selected) onChange(selected, true); }} />
    {loading ? <LoadingState /> : null}
    {error ? <ErrorState message={getApiErrorMessage(error)} action={<Button type="button" size="lg" variant="secondary"
      onClick={() => setAttempt(current => current + 1)}>{t("common.retry")}</Button>} /> : null}
    {page && !page.results.length ? <p className="text-sm text-platforma-subtle">{t("medical.reception.noOptions")}</p> : null}
    <div className="flex flex-wrap gap-2">
      {offset > 0 ? <Button type="button" size="lg" variant="secondary" disabled={disabled || loading}
        onClick={() => setOffset(Math.max(0, offset - 25))}>{t("medical.reception.previous")}</Button> : null}
      {page?.next_offset != null ? <Button type="button" size="lg" variant="secondary" disabled={disabled || loading}
        onClick={() => setOffset(page.next_offset!)}>{t("medical.reception.next")}</Button> : null}
    </div>
  </div>;
}

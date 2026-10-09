import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
export function SettingsQueryState({ queries }: { queries: Array<{ isLoading: boolean; error: unknown; refetch: () => Promise<unknown>; }>; }) {
  const { t } = useI18n();
  const error = queries.find((query) => query.error)?.error;
  if (error) return <ErrorState error={error} message={getApiErrorMessage(error)} action={<Button type="button" variant="secondary" onClick={() => { void Promise.all(queries.map((query) => query.refetch())); }}>{t("common.retry")}</Button>} />;
  return queries.some((query) => query.isLoading) ? <LoadingState /> : null;
}

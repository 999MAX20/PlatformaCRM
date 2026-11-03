import { normalizeAppError } from "../../api/appError";
import { Button } from "../../components/ui/Button";
import { InlineFallback } from "../../components/ui/FallbackSurfaces";
import { useI18n } from "../../lib/i18n";

export function RecordsLoadError({ error, retry }: { error: unknown; retry: () => void }) {
  const { t } = useI18n();
  const appError = normalizeAppError(error);
  const isReadFailure = ["validation", "not_found", "temporary", "internal"].includes(appError.category);
  const invalidFilters = appError.category === "validation" && appError.status === 400;
  return <InlineFallback error={appError}
    title={isReadFailure ? t("records.loadFailed") : undefined}
    message={isReadFailure ? t(invalidFilters ? "records.invalidFilters" : "records.loadFailedHint") : undefined}
    action={<Button onClick={retry}>{t("common.retry")}</Button>} />;
}

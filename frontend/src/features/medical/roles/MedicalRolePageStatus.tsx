import { Button } from "../../../components/ui/Button";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { getApiErrorMessage } from "../../../api/client";
import { useI18n } from "../../../lib/i18n";

export function MedicalRolePageStatus({ page, empty }: { page: { rows: unknown[]; loading: boolean; error: unknown;
  next: number | null; retry: () => void; more: () => void }; empty: string }) {
  const { t } = useI18n();
  return <>
    {page.loading ? <LoadingState /> : null}
    {page.error ? <ErrorState message={getApiErrorMessage(page.error)} action={<Button type="button" variant="secondary" onClick={page.retry}>{t("common.retry")}</Button>} /> : null}
    {!page.loading && !page.error && !page.rows.length ? <p className="text-sm text-platforma-subtle">{empty}</p> : null}
    {page.next !== null ? <Button type="button" variant="secondary" disabled={page.loading || !!page.error} onClick={page.more}>{t("medical.participation.more")}</Button> : null}
  </>;
}

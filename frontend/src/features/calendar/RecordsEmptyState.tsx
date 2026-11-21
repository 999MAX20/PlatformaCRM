import { useQuery } from "@tanstack/react-query";
import { appointmentsApi } from "../../api/appointments";
import { Button } from "../../components/ui/Button";
import { LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { RecordsLoadError } from "./RecordsLoadError";

export function RecordsEmptyState({ businessId, userId, filtered, singleDay, canCreate, onCreate, onChooseDate, onReset }: {
  businessId: number; userId?: number; filtered: boolean; singleDay: boolean;
  canCreate: boolean; onCreate: () => void; onChooseDate: () => void; onReset: () => void;
}) {
  const { t } = useI18n();
  const availability = useQuery({
    queryKey: ["appointments", "availability", businessId, userId],
    queryFn: () => appointmentsApi.workspace({ business: businessId, page_size: 1 }),
    enabled: !filtered,
  });
  if (!filtered && availability.isError) return <RecordsLoadError error={availability.error} retry={() => void availability.refetch()} />;
  if (!filtered && availability.isPending) return <LoadingState />;
  const first = !filtered && availability.data?.count === 0;
  const title = filtered ? "records.emptySearch" : first ? canCreate ? "records.emptyFirst" : "records.emptyNone" : singleDay ? "records.emptyDay" : "records.emptyPeriod";
  return <section className="flex flex-1 items-center justify-center py-8 text-center" data-testid="records-empty" aria-labelledby="records-empty-title">
    <div className="w-full max-w-lg space-y-4">
      <h2 id="records-empty-title" className="text-xl font-semibold text-platforma-text sm:text-2xl">{t(title)}</h2>
      {first && canCreate && <p className="text-sm text-platforma-subtle sm:text-base">{t("records.emptyFirstHint")}</p>}
      <div className="flex flex-wrap justify-center gap-3">
        {filtered ? <Button className="min-h-11" onClick={onReset}>{t("records.resetToday")}</Button> : <>
          {canCreate && <Button className="min-h-11" data-focus-return-id="records-empty-create" onClick={onCreate}>{t("appointments.create")}</Button>}
          {!first && <Button className="min-h-11" variant={canCreate ? "secondary" : "primary"} onClick={onChooseDate}>{t("records.chooseDate")}</Button>}
        </>}
      </div>
    </div>
  </section>;
}

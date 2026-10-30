import { useI18n } from "../../../lib/i18n";
import type { CrmCardPayload } from "../../../types";
import { StatusBadge } from "../../ui/StatusBadge";
import { drawerSurfaceClass, EmptyBlock } from "./shared";

export function EntityDealsPanel({ data }: { data: CrmCardPayload }) {
  const { t } = useI18n();
  return (
    <div className="space-y-3">
      {data.deals.length ? (
        data.deals.map((deal) => (
          <div key={deal.id} className={drawerSurfaceClass}>
            <div className="flex items-center justify-between gap-3">
              <p className="font-bold text-platforma-ink">{deal.title}</p>
              <StatusBadge status={deal.status} />
            </div>
            <p className="mt-1 text-sm text-platforma-muted">#{deal.id} · {deal.amount || 0} {deal.currency}</p>
            {deal.notes ? <p className="mt-3 text-sm leading-6 text-platforma-subtle">{deal.notes}</p> : null}
          </div>
        ))
      ) : (
        <EmptyBlock title={t("crmCard.noDeals")} text={t("crmCard.noDealsText")} />
      )}
    </div>
  );
}

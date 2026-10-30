import { formatMoney, changeStatusClass } from "./pricingPresentation";

import { usePricingChangeLogs } from "./usePricingChangeLogs";

import { Input } from "../../components/ui/Input";

import { LoadingState } from "../../components/ui/StateViews";
import { Select } from "../../components/ui/Select";

import { useI18n } from "../../lib/i18n";

type Props = {
  t: ReturnType<typeof useI18n>["t"];
  changeLogs: ReturnType<typeof usePricingChangeLogs>["changeLogs"];
  changeSearch: ReturnType<typeof usePricingChangeLogs>["changeSearch"];
  setChangeSearch: ReturnType<typeof usePricingChangeLogs>["setChangeSearch"];
  changeStatus: ReturnType<typeof usePricingChangeLogs>["changeStatus"];
  setChangeStatus: ReturnType<typeof usePricingChangeLogs>["setChangeStatus"];
  changeLogsQuery: ReturnType<typeof usePricingChangeLogs>["changeLogsQuery"];
};
export function PricingHistory({
  t,
  changeLogs,
  changeSearch,
  setChangeSearch,
  changeStatus,
  setChangeStatus,
  changeLogsQuery,
}: Props) {
  return (
    <section className="rounded-[2rem] border border-platforma-border bg-white p-5 shadow-soft">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-black text-midnight">
            {t("pricing.historyTitle")}
          </h2>
          <p className="mt-1 text-sm font-semibold text-platforma-faint">
            {t("pricing.historyText")}
          </p>
        </div>
        <span className="rounded-full bg-surface-muted px-3 py-1 text-xs font-black text-platforma-faint">
          {t("pricing.recordsCount", { count: changeLogs.length })}
        </span>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <Input
          data-testid="pricing-history-search-input"
          label={t("common.search")}
          value={changeSearch}
          onChange={(event) => setChangeSearch(event.target.value)}
          placeholder={t("pricing.historySearchPlaceholder")}
        />
        <Select
          label={t("pricing.status")}
          value={changeStatus}
          onChange={(event) => setChangeStatus(event.target.value)}
          options={[
            { value: "", label: t("pricing.allStatuses") },
            { value: "simulated", label: t("pricing.changeStatus.simulated") },
            { value: "queued", label: t("pricing.changeStatus.queued") },
            { value: "applied", label: t("pricing.changeStatus.applied") },
            { value: "blocked", label: t("pricing.changeStatus.blocked") },
            { value: "failed", label: t("pricing.changeStatus.failed") },
          ]}
        />
      </div>
      {changeLogsQuery.isLoading ? <LoadingState /> : null}
      <div className="mt-4 overflow-hidden rounded-2xl border border-platforma-border">
        {changeLogs.map((log) => (
          <article
            key={log.id}
            className="grid gap-3 border-b border-platforma-border bg-surface-muted px-4 py-3 last:border-b-0 md:grid-cols-[1.2fr_1fr_auto] md:items-center"
          >
            <div>
              <p className="text-sm font-black text-midnight">
                {log.product_name || log.product_sku}
              </p>
              <p className="mt-1 text-xs font-semibold text-platforma-faint">
                SKU {log.product_sku} ·{" "}
                {new Date(log.created_at).toLocaleString("ru-KZ")}
              </p>
            </div>
            <div className="text-sm font-black text-midnight">
              {formatMoney(log.old_price)} → {formatMoney(log.new_price)}
              {log.error ? (
                <p className="mt-1 text-xs font-semibold text-platforma-danger">
                  {t("pricing.changeFailed")}
                </p>
              ) : null}
            </div>
            <div className="flex flex-wrap items-center gap-2 md:justify-end">
              <span
                className={`rounded-full px-3 py-1 text-xs font-black ${changeStatusClass(log.status)}`}
              >
                {t(`pricing.changeStatus.${log.status}`)}
              </span>
              <span className="rounded-full bg-white px-3 py-1 text-xs font-black text-platforma-faint">
                {log.mode || "approval"}
              </span>
            </div>
          </article>
        ))}
        {!changeLogsQuery.isLoading && changeLogs.length === 0 ? (
          <div className="bg-surface-muted px-4 py-5 text-sm font-semibold text-platforma-faint">
            {t("pricing.emptyHistory")}
          </div>
        ) : null}
      </div>
    </section>
  );
}

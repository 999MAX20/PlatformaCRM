import { type KaspiPriceChangeLog } from "../../api/pricing";

export function formatMoney(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === "") return "0 ₸";
  return `${Number(value).toLocaleString("ru-KZ")} ₸`;
}

export function changeStatusClass(status: KaspiPriceChangeLog["status"]) {
  const classes: Record<KaspiPriceChangeLog["status"], string> = {
    simulated: "bg-[var(--platforma-info-soft)] text-platforma-info",
    queued: "bg-[var(--platforma-info-soft)] text-platforma-info",
    applied: "bg-[var(--platforma-success-soft)] text-platforma-success",
    blocked: "bg-[var(--platforma-warning-soft)] text-platforma-warning",
    failed: "bg-[var(--platforma-danger-soft)] text-platforma-danger",
  };
  return classes[status] || "bg-surface-muted text-platforma-subtle";
}

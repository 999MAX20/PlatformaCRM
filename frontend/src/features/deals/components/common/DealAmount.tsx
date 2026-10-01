import { money } from "../../utils/dealHelpers";

export function DealAmount({ value, currency, className = "" }: { value: string | number | null; currency?: string; className?: string }) {
  return <span className={className}>{value == null ? "—" : money(value, currency)}</span>;
}

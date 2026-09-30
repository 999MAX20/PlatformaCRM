import type { ReactNode } from "react";

export function SecuritySettingRow({ icon, title, value, action }: { icon: ReactNode; title: string; value?: ReactNode; action: ReactNode }) {
  return <div className="grid grid-cols-[36px_minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1 py-3">
    <span aria-hidden="true" className={`grid h-9 w-9 place-items-center rounded-xl bg-platforma-bg text-platforma-subtle ${value ? "row-span-2" : ""}`}>{icon}</span>
    <p className="text-sm font-semibold">{title}</p>
    <div className={`col-start-3 row-start-1 ${value ? "sm:row-span-2" : ""}`}>{action}</div>
    {value ? <div className="col-span-2 col-start-2 min-w-0 break-words text-sm text-platforma-subtle sm:col-span-1">{value}</div> : null}
  </div>;
}

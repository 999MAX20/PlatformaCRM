import { useLayoutEffect, useRef, useState } from "react";
import { MoreHorizontal } from "lucide-react";
import { ActionMenu } from "../ui/ActionMenu";
import { cn } from "../../lib/cn";
import { useI18n } from "../../lib/i18n";

export type CrmQuickTab = { value: string; label: string; count?: number };
export function CrmQuickFilters({ tabs, value, onChange, label }: { tabs: CrmQuickTab[]; value: string; onChange: (value: string) => void; label: string }) {
  const { t } = useI18n();
  const container = useRef<HTMLDivElement>(null);
  const measure = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState<string[]>(tabs.map(tab => tab.value));
  const signature = tabs.map(tab => `${tab.value}:${tab.label}:${tab.count}`).join("|");
  useLayoutEffect(() => {
    const root = container.current;
    if (!root) return;
    const fit = () => {
      const widths = Array.from(measure.current?.children || []).map(child => child.getBoundingClientRect().width);
      const available = root.clientWidth;
      if (widths.reduce((sum, width) => sum + width + 4, -4) <= available) { setVisible(tabs.map(tab => tab.value)); return; }
      const selectedIndex = Math.max(0, tabs.findIndex(tab => tab.value === value));
      const selected = tabs[selectedIndex];
      let used = (widths[selectedIndex] || 80) + 48;
      const keep = selected ? [selected.value] : [];
      tabs.forEach((tab, index) => { if (tab.value !== selected?.value && used + widths[index] + 4 <= available) { keep.push(tab.value); used += widths[index] + 4; } });
      setVisible(keep);
    };
    const observer = new ResizeObserver(fit); observer.observe(root); fit();
    return () => observer.disconnect();
  // Width changes are measured; stable textual signature avoids repeated observer setup.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signature, value]);
  const buttonClass = "platforma-focus-ring inline-flex h-10 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-control px-2.5 text-sm font-semibold";
  const content = (tab: CrmQuickTab) => <><span className="truncate">{tab.label}</span>{typeof tab.count === "number" ? <span className="rounded-sm bg-black/[0.04] px-1 text-xs font-normal tabular-nums">{tab.count}</span> : null}</>;
  const hidden = tabs.filter(tab => !visible.includes(tab.value));
  return <div ref={container} className="relative min-w-0 flex-1" role="group" aria-label={label}>
    <div aria-hidden="true" className="pointer-events-none invisible absolute h-0 w-0 overflow-hidden"><div ref={measure} className="flex w-max gap-1">{tabs.map(tab => <span key={tab.value} className={buttonClass}>{content(tab)}</span>)}</div></div>
    <div className="flex min-w-0 items-center gap-1 [&>button]:min-w-0 [&>button]:shrink">
      {tabs.filter(tab => visible.includes(tab.value)).map(tab => <button key={tab.value} type="button" aria-pressed={value === tab.value} onClick={() => onChange(tab.value)} className={cn(buttonClass, value === tab.value ? "bg-brand-50 text-platforma-text" : "text-platforma-subtle hover:bg-surface-hover")}>{content(tab)}</button>)}
      {hidden.length ? <ActionMenu label={t("crmFilters.moreQuick")} items={hidden.map(tab => ({ key: tab.value, label: `${tab.label}${typeof tab.count === "number" ? ` · ${tab.count}` : ""}`, icon: MoreHorizontal, onSelect: () => onChange(tab.value) }))} /> : null}
    </div>
  </div>;
}

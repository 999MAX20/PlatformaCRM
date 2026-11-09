import { ChevronLeft, ChevronRight } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { cn } from "../../lib/cn";
import { useI18n } from "../../lib/i18n";

function revealTab(track: HTMLDivElement | null, tabId: string) {
  const button = document.getElementById(tabId);
  if (!track || !button) return;
  const bounds = track.getBoundingClientRect();
  const tab = button.getBoundingClientRect();
  if (tab.left < bounds.left) track.scrollBy({ left: tab.left - bounds.left });
  else if (tab.right > bounds.right) track.scrollBy({ left: tab.right - bounds.right });
}

export function EntityCardTabs<T extends string>({ id, tabs, active, labels, onChange }: {
  id: string; tabs: readonly T[]; active: T; labels: Record<T, string>; onChange: (tab: T) => void;
}) {
  const { t } = useI18n();
  const track = useRef<HTMLDivElement>(null);
  const [edges, setEdges] = useState({ before: false, after: false });
  const signature = tabs.map(value => t(labels[value])).join("|");
  useEffect(() => {
    const element = track.current;
    if (!element) return;
    const measure = () => setEdges({ before: element.scrollLeft > 1, after: element.scrollLeft + element.clientWidth < element.scrollWidth - 1 });
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    element.addEventListener("scroll", measure, { passive: true });
    measure();
    return () => { observer.disconnect(); element.removeEventListener("scroll", measure); };
  }, [signature]);
  useEffect(() => {
    revealTab(track.current, `${id}-${active}`);
  }, [active, id]);
  const overflow = edges.before || edges.after;
  const arrowClass = "platforma-focus-ring flex min-h-11 w-8 shrink-0 items-center justify-center rounded-control text-platforma-subtle disabled:opacity-30";
  return <div className="sticky top-0 z-10 mb-5 flex min-w-0 shrink-0 items-center gap-1 border-b border-platforma-border bg-surface-card">
    {overflow && <button type="button" className={arrowClass} disabled={!edges.before} aria-label={`${t("clients.card.sections")}: ${t("pagination.previous")}`} onClick={() => track.current?.scrollBy({ left: -Math.max(160, track.current.clientWidth * .7) })}><ChevronLeft size={18} /></button>}
    <div ref={track} role="tablist" aria-label={t("clients.card.sections")} className="flex min-w-0 flex-1 gap-4 overflow-x-auto overscroll-x-contain [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
      {tabs.map((value, index) => <button key={value} type="button" role="tab" id={`${id}-${value}`} aria-controls={`${id}-panel`} aria-selected={active === value} tabIndex={active === value ? 0 : -1}
        data-testid={`crm-entity-tab-${value}`} className={cn("platforma-focus-ring min-h-11 shrink-0 whitespace-nowrap border-b-2 px-1 text-sm font-semibold", active === value ? "border-brand-700 text-brand-700" : "border-transparent text-platforma-subtle")}
        onClick={() => onChange(value)} onKeyDown={event => {
          if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
          event.preventDefault();
          const target = event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : (index + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length;
          const button = document.getElementById(`${id}-${tabs[target]}`);
          button?.focus();
          revealTab(track.current, `${id}-${tabs[target]}`);
          onChange(tabs[target]);
        }}>{t(labels[value])}</button>)}
    </div>
    {overflow && <button type="button" className={arrowClass} disabled={!edges.after} aria-label={`${t("clients.card.sections")}: ${t("pagination.next")}`} onClick={() => track.current?.scrollBy({ left: Math.max(160, track.current.clientWidth * .7) })}><ChevronRight size={18} /></button>}
  </div>;
}

import { Search, X } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "../../lib/cn";
import type { CrmActiveFilter, CrmControlTab } from "./CrmControlBar";

export function CrmWorkspaceToolbar<T extends string>({ search, searchLabel, onSearchChange, searchTestId, value, tabs, onChange, actions, secondaryActions, activeFilters = [], onClearFilter, onClearAll, clearAllLabel, ariaLabel }: {
  search: string;
  searchLabel: string;
  onSearchChange: (value: string) => void;
  searchTestId?: string;
  value: T;
  tabs: CrmControlTab<T>[];
  onChange: (value: T) => void;
  actions?: ReactNode;
  secondaryActions?: ReactNode;
  activeFilters?: CrmActiveFilter[];
  onClearFilter?: (id: string) => void;
  onClearAll?: () => void;
  clearAllLabel?: string;
  ariaLabel: string;
}) {
  return <div className="space-y-3">
    <div className="flex flex-wrap items-center gap-2">
      <label className="relative min-w-[180px] flex-1">
        <Search size={18} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-platforma-muted" />
        <input data-testid={searchTestId} aria-label={searchLabel} placeholder={searchLabel} value={search} onChange={(event) => onSearchChange(event.target.value)}
          className="platforma-focus-ring h-10 w-full rounded-control border border-platforma-border bg-surface-card pl-10 pr-3 text-sm text-platforma-text placeholder:text-platforma-muted" />
      </label>
      <div className="flex flex-wrap items-center gap-2">{actions}</div>
    </div>
    <div className="flex flex-wrap items-center justify-between gap-2">
      <div role="group" aria-label={ariaLabel} className="flex max-w-full items-center gap-2 overflow-x-auto pb-0.5">
        {tabs.map((tab) => <button key={tab.value} type="button" aria-pressed={value === tab.value} onClick={() => onChange(tab.value)}
          className={cn("platforma-focus-ring inline-flex h-9 shrink-0 items-center gap-2 rounded-control border px-3 text-sm font-semibold", value === tab.value ? "border-brand-300 bg-brand-50 text-platforma-text" : "border-transparent bg-surface-muted text-platforma-subtle hover:bg-surface-warm")}>
          {tab.label}{typeof tab.count === "number" ? <span className="rounded bg-black/[0.04] px-1.5 text-xs font-normal tabular-nums">{tab.count}</span> : null}
        </button>)}
      </div>
      {secondaryActions}
      {activeFilters.length ? <div className="flex flex-wrap items-center gap-2">
        {activeFilters.map((filter) => <span key={filter.id} className="inline-flex min-h-8 items-center gap-2 rounded-full bg-surface-muted px-3 text-xs text-platforma-text">
          {filter.label}: {filter.value}
          {onClearFilter ? <button type="button" className="platforma-focus-ring rounded-full p-1" aria-label={`${filter.label}: ${filter.value}`} onClick={() => onClearFilter(filter.id)}><X size={13} /></button> : null}
        </span>)}
        {onClearAll && clearAllLabel ? <button type="button" className="platforma-focus-ring rounded-control px-2 py-1 text-xs text-platforma-muted" onClick={onClearAll}>{clearAllLabel}</button> : null}
      </div> : null}
    </div>
  </div>;
}

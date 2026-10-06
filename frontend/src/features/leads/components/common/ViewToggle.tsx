import { KanbanSquare, Table2 } from "lucide-react";

import { cn } from "../../../../lib/cn";
import type { LeadViewMode, Translate } from "../../types";

const modes: Array<{ id: LeadViewMode; icon: typeof Table2; labelKey: string }> = [
  { id: "table", icon: Table2, labelKey: "leads.viewTable" },
  { id: "kanban", icon: KanbanSquare, labelKey: "leads.viewKanban" },
];

export function ViewToggle({ value, onChange, t }: { value: LeadViewMode; onChange: (mode: LeadViewMode) => void; t: Translate }) {
  return (
    <div className="flex h-10 rounded-lg border border-platforma-border bg-white p-1">
      {modes.map((mode) => {
        const Icon = mode.icon;
        return (
          <button
            key={mode.id}
            type="button"
            className={cn("grid h-8 w-8 place-items-center rounded-sm transition focus-visible-ring", value === mode.id ? "bg-platforma-border text-platforma-text" : "text-platforma-faint hover:bg-surface-hover")}
            onClick={() => onChange(mode.id)}
            aria-label={t(mode.labelKey)}
            title={t(mode.labelKey)}
          >
            <Icon size={17} />
          </button>
        );
      })}
    </div>
  );
}

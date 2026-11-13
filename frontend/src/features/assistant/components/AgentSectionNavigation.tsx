import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "../../../lib/cn";
import { useI18n } from "../../../lib/i18n";
import type { AgentSection } from "../aiAgentsTypes";
import { sectionsForAgent } from "../aiAgentsUtils";

export function AgentSectionNavigation({ scenario, value, onChange }: {
  scenario?: string; value: AgentSection; onChange: (section: AgentSection) => void;
}) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const sections = sectionsForAgent(scenario);
  const current = sections.find(section => section.id === value);
  return <nav aria-label={t("aiAgents.editorTabsAria")} className="min-w-0">
    <button type="button" className="platforma-focus-ring flex min-h-11 w-full items-center justify-between gap-3 rounded-control border border-platforma-border px-3 text-left text-sm font-semibold lg:hidden"
      aria-expanded={open} aria-controls="agent-section-links" onClick={() => setOpen(!open)}>
      {t(current?.labelKey || "aiAgents.section.test")}
      <ChevronDown size={16} aria-hidden="true" />
    </button>
    <div id="agent-section-links" className={cn("mt-2 space-y-1 lg:mt-0 lg:block", !open && "hidden")}>
      {sections.map((section, index) => <button key={section.id} type="button"
        aria-current={value === section.id ? "page" : undefined}
        className={cn("platforma-focus-ring flex min-h-11 w-full items-center gap-3 rounded-control px-3 py-2 text-left text-sm transition hover:bg-surface-hover",
          value === section.id ? "bg-brand-50 font-semibold text-brand-800" : "text-platforma-subtle",
          index > 0 && section.id === "profile" && "!mt-4")}
        onClick={() => { setOpen(false); onChange(section.id); }}>
        <section.icon size={17} aria-hidden="true" className="shrink-0" />
        <span className="min-w-0 break-words">{t(section.labelKey)}</span>
      </button>)}
    </div>
  </nav>;
}

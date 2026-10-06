import { ChartNoAxesCombined, CircleHelp, MessageSquareText } from "lucide-react";
import { useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useI18n } from "../../../lib/i18n";

export function AgentScenarioCard({ value, selected, unavailable, onSelect }: {
  value: "inbox" | "crm"; selected: boolean; unavailable: boolean; onSelect: () => void;
}) {
  const { t } = useI18n();
  const id = useId();
  const [hintOpen, setHintOpen] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const hintRef = useRef<HTMLDivElement>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const [position, setPosition] = useState<{ left: number; top: number; width: number } | null>(null);
  const showHint = () => { clearTimeout(closeTimer.current); setHintOpen(true); };
  const hideHint = () => { closeTimer.current = setTimeout(() => {
    if (document.activeElement !== triggerRef.current) setHintOpen(false);
  }, 120); };
  useEffect(() => () => clearTimeout(closeTimer.current), []);
  useLayoutEffect(() => {
    if (!hintOpen) return;
    const place = () => {
      const card = cardRef.current?.getBoundingClientRect();
      const dialog = cardRef.current?.closest('[role="dialog"]')?.getBoundingClientRect();
      if (!card || !dialog) return;
      const left = dialog.right + 12;
      const width = Math.min(320, window.innerWidth - left - 12);
      setPosition(width >= 220 ? { left, width,
        top: Math.max(12, Math.min(card.top, window.innerHeight - (hintRef.current?.offsetHeight || 160) - 12)),
      } : null);
    };
    place();
    window.addEventListener("resize", place);
    window.addEventListener("scroll", place, true);
    return () => { window.removeEventListener("resize", place); window.removeEventListener("scroll", place, true); };
  }, [hintOpen]);
  const Icon = value === "inbox" ? MessageSquareText : ChartNoAxesCombined;
  const hint = hintOpen && <div ref={hintRef} id={id} role="tooltip"
    onMouseEnter={showHint} onMouseLeave={hideHint}
    style={position ? { ...position, zIndex: "calc(var(--platforma-z-modal) + 1)" } : undefined}
    className={`${position ? "fixed" : "mt-2 w-full"} rounded-control border border-platforma-border bg-surface-card p-3 text-sm text-platforma-text shadow-lg`}>{t(`aiScenario.${value}Help`)}</div>;
  return <div ref={cardRef} className={`relative flex flex-wrap items-start gap-2 rounded-xl border p-4 ${selected ? "border-brand-600 bg-surface-card" : "border-platforma-border bg-surface-card"} ${unavailable ? "border-disabled-border bg-disabled-surface text-disabled-content" : ""}`}
    onKeyDown={event => { if (event.key === "Escape" && hintOpen) { event.preventDefault(); event.stopPropagation(); setHintOpen(false); } }}>
    <label className={`flex flex-1 items-start gap-3 ${unavailable ? "cursor-not-allowed" : "cursor-pointer"}`}>
      <input type="radio" name="agent-scenario" value={value} checked={selected} disabled={unavailable} onChange={onSelect} className="mt-1" />
      <Icon size={20} aria-hidden="true" className="mt-0.5 shrink-0" />
      <span><span className="block text-sm font-semibold">{t(`aiScenario.${value}`)}</span>
        <span className="mt-1 block text-sm text-platforma-subtle">{t(`aiScenario.${value}Description`)}</span>
        {unavailable && <span className="mt-2 block text-sm">{t("aiScenario.alreadyExists")}</span>}
      </span>
    </label>
    <button ref={triggerRef} type="button" className="platforma-focus-ring flex min-h-11 min-w-11 shrink-0 items-center justify-center rounded-control text-platforma-subtle hover:bg-surface-hover"
      aria-label={t("aiScenario.help", { name: t(`aiScenario.${value}`) })} aria-describedby={hintOpen ? id : undefined}
      onMouseEnter={showHint} onMouseLeave={hideHint}
      onFocus={showHint} onBlur={() => setHintOpen(false)} onClick={showHint}>
      <CircleHelp size={18} aria-hidden="true" />
    </button>
    {position ? createPortal(hint, document.body) : hint}
  </div>;
}

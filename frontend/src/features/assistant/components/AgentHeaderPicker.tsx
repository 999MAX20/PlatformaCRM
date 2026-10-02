import { Check, ChevronDown, Search } from "lucide-react";
import { useEffect, useId, useMemo, useRef, useState } from "react";

import { getApiErrorMessage } from "../../../api/client";
import { Badge } from "../../../components/ui/Badge";
import { Button } from "../../../components/ui/Button";
import { PopoverSurface } from "../../../components/ui/Overlay";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { cn } from "../../../lib/cn";
import { useI18n } from "../../../lib/i18n";
import type { AgentProfile, Bot, Id } from "../../../types";

export function AgentHeaderPicker({ bots, profiles, selectedBot, isLoading, error, onRetry, onSelect }: {
  bots: Bot[];
  profiles: AgentProfile[];
  selectedBot: Bot | null;
  isLoading: boolean;
  error: unknown;
  onRetry: () => void;
  onSelect: (id: Id) => void;
}) {
  const { t } = useI18n();
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const listId = useId();
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const options = useMemo(() => bots.map(bot => ({
    bot,
    role: profiles.find(profile => profile.bot === bot.id)?.role_description || "",
  })).filter(({ bot, role }) => `${bot.name} ${role}`.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase())), [bots, profiles, search]);
  const activeOption = options[activeIndex];

  useEffect(() => {
    if (!open) return;
    const frame = requestAnimationFrame(() => inputRef.current?.focus());
    const closeOutside = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", closeOutside);
    return () => {
      cancelAnimationFrame(frame);
      document.removeEventListener("pointerdown", closeOutside);
    };
  }, [open]);

  useEffect(() => {
    listRef.current?.querySelector<HTMLElement>(`[data-active="true"]`)?.scrollIntoView({ block: "nearest" });
  }, [activeIndex, open]);

  function openPicker() {
    setSearch("");
    setActiveIndex(Math.max(0, bots.findIndex(bot => bot.id === selectedBot?.id)));
    setOpen(true);
  }

  function closePicker() {
    setOpen(false);
    triggerRef.current?.focus();
  }

  function selectAgent(id: Id) {
    // Return focus before navigation so an unsaved-draft dialog can take it.
    closePicker();
    onSelect(id);
  }

  return (
    <div ref={rootRef} className="relative w-[180px] shrink-0" onBlur={event => {
      if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
    }} onKeyDown={event => {
      if (event.key === "Escape" && open) {
        event.preventDefault();
        event.stopPropagation();
        closePicker();
      }
    }}>
      <Button ref={triggerRef} type="button" variant="secondary" className="min-h-11 w-full justify-between gap-2 px-3 xl:min-h-10"
        data-testid="agent-header-picker" aria-haspopup="listbox" aria-expanded={open} aria-controls={open ? listId : undefined}
        title={selectedBot?.name || t("aiAgents.allAgents")} aria-label={`${t("aiAgents.agentPickerAria")}: ${selectedBot?.name || t("aiAgents.allAgents")}`}
        onClick={() => open ? closePicker() : openPicker()} onKeyDown={event => {
          if (event.key === "ArrowDown" || event.key === "ArrowUp") { event.preventDefault(); openPicker(); }
        }}>
        <span className="min-w-0 truncate">{selectedBot?.name || t("aiAgents.allAgents")}</span>
        <ChevronDown aria-hidden="true" size={16} className="shrink-0" />
      </Button>
      {open ? (
        <PopoverSurface className="absolute right-0 top-full z-50 mt-1 w-[min(420px,calc(100vw-24px))] overflow-hidden xl:left-1/2 xl:right-auto xl:-translate-x-1/2" data-testid="agent-picker-popover">
          <div className="border-b border-platforma-border p-2">
            <div className="relative">
              <Search aria-hidden="true" size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-platforma-subtle" />
              <input ref={inputRef} role="combobox" aria-label={t("aiAgents.pickerSearch")} aria-expanded="true" aria-controls={listId}
                aria-autocomplete="list" aria-activedescendant={!isLoading && !error && activeOption ? `${listId}-${activeOption.bot.id}` : undefined}
                placeholder={t("aiAgents.pickerSearch")} value={search}
                className="platforma-focus-ring min-h-11 w-full rounded-control border border-platforma-control bg-surface-card pl-9 pr-3 text-sm text-platforma-text placeholder:text-platforma-subtle"
                onChange={event => { setSearch(event.target.value); setActiveIndex(0); }}
                onKeyDown={event => {
                  if (isLoading || error || !options.length) return;
                  if (["ArrowDown", "ArrowUp"].includes(event.key)) {
                    event.preventDefault();
                    setActiveIndex(current => (current + (event.key === "ArrowDown" ? 1 : -1) + options.length) % options.length);
                  } else if (event.key === "Enter" && activeOption) {
                    event.preventDefault();
                    selectAgent(activeOption.bot.id);
                  }
                }} />
            </div>
          </div>
          {isLoading ? <LoadingState label={t("aiAgents.loading")} /> : error ? (
            <ErrorState message={getApiErrorMessage(error)} action={<Button variant="secondary" onClick={onRetry}>{t("common.retry")}</Button>} />
          ) : null}
          <div ref={listRef} id={listId} role="listbox" aria-label={t("aiAgents.allAgents")} className="max-h-[min(360px,calc(100dvh-200px))] overflow-y-auto overscroll-contain p-1">
            {!isLoading && !error ? options.map(({ bot, role }, index) => (
              <div key={bot.id} id={`${listId}-${bot.id}`} role="option" aria-selected={bot.id === selectedBot?.id} data-active={activeIndex === index}
                className={cn("flex min-h-14 cursor-pointer items-start gap-2 rounded-control px-3 py-2 text-sm transition hover:bg-surface-hover",
                  activeIndex === index && "bg-surface-hover", bot.id === selectedBot?.id && "bg-ai-50")}
                onMouseDown={event => event.preventDefault()} onClick={() => selectAgent(bot.id)}>
                <span className="mt-0.5 w-4 shrink-0">{bot.id === selectedBot?.id ? <Check aria-hidden="true" size={16} className="text-ai-700" /> : null}</span>
                <div className="min-w-0 flex-1">
                  <p className="break-words font-semibold text-platforma-text">{bot.name}</p>
                  <p className="mt-0.5 break-words text-xs leading-5 text-platforma-subtle">{role || t("aiAgents.purposeMissing")}</p>
                </div>
                <div className="flex max-w-[120px] shrink-0 flex-col items-end gap-1">
                  <Badge size="sm" variant={bot.status === "active" ? "success" : "neutral"}>{t(`aiAgents.status.${bot.status}`)}</Badge>
                  {bot.readiness && !bot.readiness.is_ready ? <span className="text-right text-xs text-platforma-warning">{t("aiAgents.setupIncomplete")}</span> : null}
                </div>
              </div>
            )) : null}
          </div>
          {!isLoading && !error && !options.length ? <p role="status" className="px-4 py-5 text-sm text-platforma-subtle">{t(bots.length ? "common.noResults" : "aiAgents.emptyAgentsTitle")}</p> : null}
        </PopoverSurface>
      ) : null}
    </div>
  );
}

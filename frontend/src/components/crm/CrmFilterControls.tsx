import { Search, SlidersHorizontal, X, BookmarkPlus, Trash2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { useAuth } from "../../features/auth/AuthProvider";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { dateInTimeZone } from "../../lib/format";
import { useI18n } from "../../lib/i18n";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { Select } from "../ui/Select";
import { isCalendarDate } from "../ui/DateRangePicker";
import { CalendarPopover } from "../ui/CalendarPopover";
import { CustomFieldFilterFields, validCustomFieldFilter } from "./CustomFieldFilterFields";
import type { CustomFieldDefinition } from "../../types";
import { Dialog } from "../ui/Overlay";
import { CrmQuickFilters } from "./CrmQuickFilters";
import { CrmFilterFields, fieldOptions, filterFields, type FilterOptions } from "./CrmFilterFields";
import { crmFilterDefaults, crmFilterKeysFor, useCrmFilters, type CrmFilterKind, type CrmFilterValues } from "./useCrmFilters";

type SavedView = { id: string; name: string; values: CrmFilterValues };
export function CrmFilterControls({ kind, searchLabel, counts, options = {}, actions, context, extraFilterAction, compact = false, customDefinitions = [] }: {
  kind: CrmFilterKind; searchLabel: string; counts?: Record<string, number | undefined>; options?: FilterOptions;
  actions?: ReactNode; context?: ReactNode; extraFilterAction?: ReactNode;
  compact?: boolean; customDefinitions?: CustomFieldDefinition[];
}) {
  const { t } = useI18n();
  const { user } = useAuth();
  const { business } = useActiveBusiness();
  const { state, update, reset } = useCrmFilters(kind);
  const defaults = crmFilterDefaults(kind);
  const [open, setOpen] = useState(false);
  const trigger = useRef<HTMLButtonElement>(null);
  const close = useCallback((restoreFocus = true) => { setOpen(false); if (restoreFocus) trigger.current?.focus({ preventScroll: true }); }, []);
  const [draft, setDraft] = useState(state);
  const [error, setError] = useState("");
  const [presetName, setPresetName] = useState("");
  const storageKey = `platforma.crm.views.v1.${business?.id}.${user?.id}.${kind}`;
  const [saved, setSaved] = useState<{ key: string; views: SavedView[] }>({ key: "", views: [] });
  const views = saved.key === storageKey ? saved.views : [];
  useEffect(() => {
    try {
      const raw: unknown = JSON.parse(localStorage.getItem(storageKey) || "[]");
      const valid = Array.isArray(raw) ? raw.filter((item): item is SavedView => item && typeof item.id === "string" && typeof item.name === "string" && item.values && typeof item.values === "object" && Object.values(item.values).every(value => typeof value === "string")).slice(0, 12) : [];
      setSaved({ key: storageKey, views: valid });
    } catch { setSaved({ key: storageKey, views: [] }); }
    setOpen(false);
  }, [storageKey]);
  function saveViews(next: SavedView[]) {
    try { localStorage.setItem(storageKey, JSON.stringify(next)); setSaved({ key: storageKey, views: next }); }
    catch { setError(t("crmFilters.saveError")); }
  }
  function start() { setDraft({ ...state }); setError(""); setOpen(true); }
  function validation(value: CrmFilterValues) {
    if (compact && kind !== "clients" && !validCustomFieldFilter(value, customDefinitions)) return t("clients.invalidCustomFilter");
    for (const key of ["created_from", "created_to", "expected_close_from", "expected_close_to", "appointment_from", "appointment_to"]) if (value[key] && !isCalendarDate(value[key])) return t("crmFilters.invalidDate");
    for (const prefix of ["created", "expected_close", "appointment"]) if (value[`${prefix}_from`] && value[`${prefix}_to`] && value[`${prefix}_from`] > value[`${prefix}_to`]) return t("crmFilters.invalidRange");
    if (value.appointment === "period" && !value.appointment_from && !value.appointment_to) return t("crmFilters.appointmentDateRequired");
    if ((value.amount_min && Number(value.amount_min) < 0) || (value.amount_max && Number(value.amount_max) < 0) || (value.amount_min && value.amount_max && Number(value.amount_min) > Number(value.amount_max))) return t("crmFilters.invalidAmount");
    return "";
  }
  const keys = kind === "clients" ? ["no_reply"] : kind === "leads" ? ["new", "in_progress", "attention"] : ["hot", "no_tasks"];
  const tabs = keys.map(value => ({ value, label: t(`crmFilters.quick.${value}`), count: counts?.[value === "all" ? "total" : value] }));
  const fields = filterFields(kind);
  const chips = fields.flatMap(key => {
    if (key === "statuses") return []; // The always-visible status control carries this condition.
    if (["created", "expected_close", "amount"].includes(key)) {
      const from = key === "amount" ? "amount_min" : `${key}_from`;
      const to = key === "amount" ? "amount_max" : `${key}_to`;
      return state[from] || state[to] ? [{ key, label: t(kind === "clients" && key === "created" ? "crmFilters.added" : `crmFilters.${key}`), value: `${state[from] || "…"} – ${state[to] || "…"}`, clear: { [from]: "", [to]: "" } }] : [];
    }
    if (!state[key] || state[key] === defaults[key]) return [];
    const selected = state[key].split(",");
    const available = fieldOptions(kind, key, options, t);
    const display = key === "appointment" && state.appointment === "period" ? `${state.appointment_from || "…"} – ${state.appointment_to || "…"}` : key === "archive" ? t(`crmFilters.archive.${state.archive}`) : key === "handoff" ? t("crmFilters.handoff") : selected.map(value => available.find(option => String(option.value) === value)?.label || value).join(", ");
    return [{ key, label: t(`crmFilters.${key}`), value: key === "tag" && selected.length > 1 ? `${display} · ${t(state.tag_mode === "all" ? "crmFilters.tagAll" : "crmFilters.tagAny")}` : display, clear: { [key]: defaults[key] } }];
  });
  const statusText = kind === "clients" ? t(`crmFilters.archive.${state.archive}`) : state.statuses === defaults.statuses ? t(kind === "leads" ? "crmFilters.unfinished" : "crmFilters.openDeals")
    : state.statuses === "all" ? t("crmFilters.allStatuses") : state.statuses.split(",").map(value => t(`crmFilters.status.${value}`)).join(", ");
  const form = (
      <form onKeyDown={event => { if (event.key === "Escape" && event.defaultPrevented) event.stopPropagation(); }} onSubmit={event => { event.preventDefault(); const message = validation(draft); if (message) { setError(message); return; } update(draft); close(); }} className="space-y-5">
        <CrmFilterFields kind={kind} value={draft} onChange={patch => { setError(""); setDraft(current => ({ ...current, ...patch, ...(patch.assignees ? { scope: "all" } : {}) })); }} options={options} today={dateInTimeZone(new Date().toISOString(), business?.timezone || "UTC")} />
        {compact && kind !== "clients" && <CustomFieldFilterFields definitions={customDefinitions} value={draft} onChange={patch => { setError(""); setDraft(current => ({ ...current, ...patch })); }} />}
        {kind !== "clients" && extraFilterAction && <div onClick={() => close(false)}>{extraFilterAction}</div>}
        {kind !== "clients" && <details className="rounded-control border border-platforma-border p-3"><summary className="platforma-focus-ring cursor-pointer text-sm font-medium">{t("crmFilters.savedViews")}</summary>
          <div className="mt-3 space-y-2">{views.map(view => <div key={view.id} className="flex items-center gap-2"><Button type="button" variant="secondary" size="sm" className="min-w-0 flex-1 justify-start" onClick={() => { const next = { ...defaults, ...Object.fromEntries(crmFilterKeysFor(kind).filter(key => typeof view.values[key] === "string").map(key => [key, view.values[key]])) }; setDraft(next); }}><span className="truncate">{view.name}</span></Button><Button type="button" size="icon" variant="ghost" aria-label={`${t("crmFilters.remove")}: ${view.name}`} onClick={() => saveViews(views.filter(item => item.id !== view.id))}><Trash2 size={15} /></Button></div>)}
            <Input label={t("crmFilters.viewName")} value={presetName} maxLength={80} onChange={event => setPresetName(event.target.value)} />
            <Button type="button" variant="secondary" size="sm" disabled={!presetName.trim()} onClick={() => { const message = validation(draft); if (message) { setError(message); return; } saveViews([{ id: crypto.randomUUID(), name: presetName.trim(), values: { ...draft } }, ...views].slice(0, 12)); setPresetName(""); }}><BookmarkPlus size={15} />{t("crmFilters.saveView")}</Button>
          </div>
        </details>}
        {error ? <p role="alert" className="text-sm text-platforma-danger">{error}</p> : null}
        <div className="sticky bottom-0 flex flex-wrap justify-between gap-2 border-t border-platforma-border bg-platforma-card pt-3">
          <Button type="button" variant="ghost" onClick={() => { setDraft({ ...defaults, pipeline: state.pipeline }); setError(""); }}>{t("common.reset")}</Button>
          <div className="flex gap-2"><Button type="button" variant="secondary" onClick={() => close()}>{t("common.cancel")}</Button><Button type="submit">{t("crmFilters.apply")}</Button></div>
        </div>
      </form>
  );
  const appliedCount = chips.length + (state.custom_field ? 1 : 0);
  if (compact) return <div data-testid={`${kind}-unified-toolbar`} className="space-y-2"><div className="flex flex-wrap items-center gap-2 px-1 lg:flex-nowrap lg:overflow-x-auto">
    <label className="relative w-full lg:w-[var(--global-search-width,480px)] max-w-full min-w-0 shrink-0">
      <Search size={17} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-platforma-muted" />
      <input aria-label={searchLabel} placeholder={searchLabel} data-testid={`${kind}-search-input`} value={state.search} onChange={event => update({ search: event.target.value }, true)} className="platforma-focus-ring h-10 w-full rounded-control border border-platforma-control bg-platforma-card pl-9 pr-3 text-sm text-platforma-text placeholder:text-platforma-muted max-sm:h-11" />
    </label>
    <Button type="button" variant={state.quick === "no_reply" ? "primary" : "secondary"} className="h-10 shrink-0 whitespace-nowrap max-sm:h-11" aria-pressed={state.quick === "no_reply"} onClick={() => update({ quick: state.quick === "no_reply" ? "all" : "no_reply", archive: "active" })}>
      {t("crmFilters.quick.no_reply")}{typeof counts?.no_reply === "number" ? <span className="text-xs tabular-nums">{counts.no_reply}</span> : null}
    </Button>
    <Button ref={trigger} data-focus-return-id={`${kind}-filters`} type="button" variant="secondary" className="h-10 shrink-0 gap-2 max-sm:h-11" aria-haspopup="dialog" aria-expanded={open} onClick={() => open ? close() : start()}><SlidersHorizontal size={16} />{t("crmFilters.filters")}{appliedCount > 0 && <span className="text-xs tabular-nums">{appliedCount}</span>}</Button>
    <div className="flex shrink-0 items-center gap-2">{actions}</div>
    {state.search || state.quick !== "all" || appliedCount > 0 ? <Button type="button" size="icon" variant="ghost" className="h-10 w-10 shrink-0 max-sm:h-11 max-sm:w-11" aria-label={t("common.reset")} title={t("common.reset")} onClick={reset}><X size={16} /></Button> : null}
    </div>
    {chips.length > 0 && <div className="flex flex-wrap gap-2 px-1" aria-label={t("crmFilters.activeFilters")}>
      {chips.map(chip => <button key={chip.key} type="button" onClick={() => update(chip.clear)} className="platforma-focus-ring inline-flex min-h-8 max-sm:min-h-11 max-w-full items-center gap-2 rounded-control bg-surface-muted px-2 text-left text-xs text-platforma-text" aria-label={`${t("crmFilters.remove")}: ${chip.label}: ${chip.value}`}><span className="min-w-0 break-words">{chip.label}: {chip.value}</span><X size={13} className="shrink-0" /></button>)}
    </div>}
    {open && <CalendarPopover anchor={trigger} label={t("crmFilters.filters")} onClose={close} testId={`${kind}-filters-panel`}>{form}</CalendarPopover>}
  </div>;
  return <div className="space-y-2" data-testid={`${kind}-unified-toolbar`}>
    <div className="flex flex-wrap items-center gap-2">
      <label className="relative w-[var(--global-search-width,480px)] max-w-full min-w-0 shrink-0 lg:order-1">
        <Search size={17} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-platforma-muted" />
        <input aria-label={searchLabel} placeholder={searchLabel} data-testid={`${kind}-search-input`} value={state.search} onChange={event => update({ search: event.target.value }, true)} className="platforma-focus-ring h-11 w-full rounded-control border border-platforma-control bg-platforma-card pl-9 pr-3 text-sm text-platforma-text placeholder:text-platforma-muted lg:h-10" />
      </label>
      <div className="order-2 ml-auto flex shrink-0 items-center gap-1 lg:order-4">
        <Button type="button" variant="secondary" size="sm" className="h-11 gap-1.5 lg:h-10" data-focus-return-id={`${kind}-filters`} aria-haspopup="dialog" onClick={start}><SlidersHorizontal size={16} /><span>{t("crmFilters.filters")}</span>{chips.length ? <span className="text-xs tabular-nums">{chips.length}</span> : null}</Button>
        <div className="flex items-center gap-1 max-lg:[&_button]:h-11 max-lg:[&_button]:min-w-11 max-lg:[&_button]:gap-0 max-lg:[&_button]:px-2.5 max-lg:[&_button]:text-[0px]">{actions}</div>
      </div>
      {kind !== "clients" ? <div className="order-1 min-w-0 shrink-0 lg:order-2"><Select density="compact" portal aria-label={t("crmFilters.scope")} value={state.scope} onChange={event => update({ scope: event.target.value })} options={["all", "mine"].map(value => ({ value, label: t(`crmFilters.scope.${kind}.${value}`) }))} className="h-11 w-36 px-2 py-1 lg:h-10 lg:min-h-10 lg:w-40" /></div> : null}
      <div className="order-3 flex w-full min-w-0 items-center gap-2 lg:w-auto lg:flex-1">
      <div className="flex min-w-0 flex-1 items-center"><CrmQuickFilters label={t("crmFilters.quickFilters")} tabs={tabs} value={state.quick} onChange={value => update({ quick: value === state.quick ? "all" : value })} /></div>
      {context}
      </div>
    </div>

    <div className="flex flex-wrap items-center gap-1.5" aria-label={t("crmFilters.activeFilters")}>
      <span className="mr-1 text-xs text-platforma-muted" data-testid={`${kind}-filter-status`}>{t(kind === "clients" ? "crmFilters.archive" : "crmFilters.statuses")}: {statusText}</span>
      {chips.map(chip => <button key={chip.key} type="button" onClick={() => update(chip.clear)} className="platforma-focus-ring inline-flex min-h-7 max-w-full items-center gap-2 rounded-control bg-surface-muted px-2 text-xs text-platforma-text" aria-label={`${t("crmFilters.remove")}: ${chip.label}: ${chip.value}`}><span className="truncate">{chip.label}: {chip.value}</span><X size={13} className="shrink-0" /></button>)}
      {chips.length || state.quick !== "all" || state.scope !== "all" || state.statuses !== defaults.statuses ? <Button type="button" size="sm" variant="ghost" className="min-h-7 py-0.5" onClick={reset}>{t("common.reset")}</Button> : null}
    </div>
    <Dialog title={t("crmFilters.filters")} open={open} onClose={() => setOpen(false)} size="sm" focusReturnId={`${kind}-filters`} bodyClassName="p-4 sm:p-5">
      {form}
    </Dialog>
  </div>;
}

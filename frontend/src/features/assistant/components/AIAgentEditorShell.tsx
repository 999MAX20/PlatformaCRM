import { MessageSquareText, PanelRightOpen } from "lucide-react";
import type { ReactNode } from "react";

import { Badge } from "../../../components/ui/Badge";
import { Button } from "../../../components/ui/Button";
import { Switch } from "../../../components/ui/Switch";
import { cn } from "../../../lib/cn";
import { useI18n } from "../../../lib/i18n";
import type { Bot } from "../../../types";
import type { AgentSection } from "../aiAgentsTypes";
import { agentStatusLabel, sectionsForAgent } from "../aiAgentsUtils";
import { AgentSectionNavigation } from "./AgentSectionNavigation";

export function AIAgentEditorShell({
  bot, activeSection, canManage, activationBlocked, dirty, hasUserEdits, profileExists,
  saveDisabled, isSaving, saveState, onSectionChange, onToggleStatus,
  onOpenMessages, onReset, onSave, showFooter, children, afterFooter,
  navigation, readiness, preview, previewOpen, onOpenPreview,
}: {
  bot: Bot;
  activeSection: AgentSection;
  canManage: boolean;
  activationBlocked: boolean;
  dirty: boolean;
  hasUserEdits: boolean;
  profileExists: boolean;
  saveDisabled?: boolean;
  isSaving: boolean;
  saveState: "idle" | "saved";
  onSectionChange: (section: AgentSection) => void;
  onToggleStatus: (active: boolean) => void;
  onOpenMessages: () => void;
  onReset: () => void;
  onSave: () => void;
  showFooter: boolean;
  children: ReactNode;
  afterFooter?: ReactNode;
  navigation: ReactNode;
  readiness: ReactNode;
  preview?: ReactNode;
  previewOpen: boolean;
  onOpenPreview: () => void;
}) {
  const { t } = useI18n();
  const runtimeBlocked = bot.status === "active" && Boolean(bot.readiness && !bot.readiness.is_ready);
  const section = sectionsForAgent(bot.scenario).find(item => item.id === activeSection);
  return (
    <section className="ai-agent-editor grid min-w-0 gap-5 lg:grid-cols-[216px_minmax(0,1fr)] lg:gap-8"
      aria-label={t("aiAgents.editorAria", { name: bot.name })} data-testid="ai-agent-editor">
      <aside className="min-w-0 space-y-4 lg:sticky lg:top-[calc(var(--app-header-height)+1.5rem)] lg:self-start" aria-label={t("aiAgents.allAgents")}>
        {navigation}
        <AgentSectionNavigation scenario={bot.scenario} value={activeSection} onChange={onSectionChange} />
      </aside>
      <div className="min-w-0">
        <header className="border-b border-platforma-border pb-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0 flex-1 basis-60">
              <h2 className="break-words text-xl font-semibold text-platforma-ink">{bot.name}</h2>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <span className="text-sm text-platforma-subtle">{t(`aiScenario.${bot.scenario || "inbox"}`)}</span>
                <Badge size="sm" variant={runtimeBlocked ? "warning" : bot.status === "active" ? "success" : "neutral"}>{agentStatusLabel(bot, t)}</Badge>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {bot.scenario !== "crm" && <>
                {activeSection !== "test" && <Button type="button" variant="secondary" className="min-h-11" disabled={isSaving}
                  data-focus-return-id="agent-preview-trigger" aria-expanded={previewOpen} onClick={onOpenPreview}>
                  <PanelRightOpen size={16} aria-hidden="true" />{t("aiAgents.openPreview")}
                </Button>}
                <Button type="button" className="min-h-11" variant="secondary" aria-label={t("aiAgents.openMessages")} title={t("aiAgents.openMessages")} onClick={onOpenMessages}>
                  <MessageSquareText aria-hidden="true" size={16} /><span className="hidden sm:inline">{t("aiAgents.openMessages")}</span>
                </Button>
              </>}
            </div>
          </div>
          <div className="mt-3 flex flex-wrap items-center justify-between gap-x-6 gap-y-2">
            <div className="min-w-0 basis-full sm:flex-1 sm:basis-auto">{readiness}</div>
            <label className="flex min-h-11 items-center gap-3 text-sm text-platforma-subtle">
              <span>{t(bot.status === "active" ? "aiAgents.activityOn" : "aiAgents.activityOff")}</span>
              <Switch checked={bot.status === "active"} disabled={!canManage || activationBlocked || (dirty && bot.status !== "active")}
                isLoading={isSaving} label={t("aiAgents.statusSwitch", { name: bot.name })} onChange={onToggleStatus} size="dense" tone="brand"
                title={activationBlocked ? t("aiAgents.activationBlocked") : dirty && bot.status !== "active" ? t("aiSetup.saveBeforeTest") : undefined} />
            </label>
          </div>
        </header>
        <div className={cn("grid min-w-0 gap-6", previewOpen && "xl:grid-cols-[minmax(0,1fr)_360px]")}>
          <div className="min-w-0">
            <div id={`ai-agent-editor-panel-${activeSection}`} className="min-w-0 py-6">
              <h3 className="mb-5 text-lg font-semibold text-platforma-ink">{t(section?.labelKey || "aiAgents.section.test")}</h3>
              <fieldset disabled={isSaving} className="min-w-0 w-full">{children}</fieldset>
            </div>
            {canManage && showFooter && <footer className={cn("bottom-[calc(4.375rem_+_max(0.25rem,env(safe-area-inset-bottom)))] z-10 flex flex-wrap items-center justify-between gap-3 border-t border-platforma-border bg-surface py-4 lg:sticky lg:bottom-0", dirty ? "sticky" : "relative bottom-auto")} data-testid="agent-save-bar">
              <p className="text-sm text-platforma-subtle" aria-live="polite">
                {hasUserEdits ? t("aiAgents.unsavedIndicator") : dirty ? t(profileExists ? "aiAgents.profileInactive" : "aiAgents.profileNotSaved") : saveState === "saved" ? t("aiAgents.savedIndicator") : t("aiAgents.configurationSaved")}
              </p>
              <div className="flex flex-wrap gap-2">
                <Button type="button" className="min-h-11" variant="secondary" disabled={!hasUserEdits || isSaving} onClick={onReset}>{t("common.cancel")}</Button>
                <Button type="button" className="min-h-11" disabled={!dirty || saveDisabled} isLoading={isSaving} onClick={onSave}>{t("aiAgents.saveChanges")}</Button>
              </div>
            </footer>}
            {afterFooter}
          </div>
          {preview}
        </div>
      </div>
    </section>
  );
}

import { MessageSquareText } from "lucide-react";
import { useLayoutEffect, useRef, type ReactNode } from "react";

import { Badge } from "../../../components/ui/Badge";
import { Button } from "../../../components/ui/Button";
import { Switch } from "../../../components/ui/Switch";
import { Tabs } from "../../../components/ui/Tabs";
import { useI18n } from "../../../lib/i18n";
import type { Bot as BotType } from "../../../types";
import type { AgentSection } from "../aiAgentsTypes";
import { agentStatusLabel, sectionsForAgent } from "../aiAgentsUtils";

type SaveState = "idle" | "saved";

function statusVariant(status: BotType["status"], runtimeBlocked: boolean) {
  if (runtimeBlocked) return "warning" as const;
  if (status === "active") return "success" as const;
  if (status === "paused") return "warning" as const;
  return "neutral" as const;
}

export function AIAgentEditorShell({
  bot,
  activeSection,
  canManage,
  activationBlocked,
  dirty,
  saveDisabled,
  isSaving,
  saveState,
  onSectionChange,
  onToggleStatus,
  onOpenMessages,
  onReset,
  onSave,
  showFooter,
  children,
  afterFooter,
}: {
  bot: BotType;
  activeSection: AgentSection;
  canManage: boolean;
  activationBlocked: boolean;
  dirty: boolean;
  saveDisabled?: boolean;
  isSaving: boolean;
  saveState: SaveState;
  onSectionChange: (section: AgentSection) => void;
  onToggleStatus: (active: boolean) => void;
  onOpenMessages: () => void;
  onReset: () => void;
  onSave: () => void;
  showFooter: boolean;
  children: ReactNode;
  afterFooter?: ReactNode;
}) {
  const { t } = useI18n();
  const headerRef = useRef<HTMLElement>(null);
  const runtimeBlocked = bot.status === "active" && Boolean(bot.readiness && !bot.readiness.is_ready);
  const statusLabel = agentStatusLabel(bot, t);
  const sections = sectionsForAgent(bot.scenario);
  const nextSection = sections[sections.findIndex((section) => section.id === activeSection) + 1];
  useLayoutEffect(() => {
    const list = headerRef.current?.querySelector<HTMLElement>('[role="tablist"]');
    const tab = list?.querySelector<HTMLElement>('[aria-selected="true"]');
    if (!list || !tab) return;
    const parent = list.getBoundingClientRect();
    const selected = tab.getBoundingClientRect();
    if (selected.right > parent.right) list.scrollLeft += selected.right - parent.right;
    else if (selected.left < parent.left) list.scrollLeft += selected.left - parent.left;
  }, [activeSection]);

  return (
    <section
      className="min-w-0"
      aria-label={t("aiAgents.editorAria", { name: bot.name })}
      data-testid="ai-agent-editor"
    >
      <header ref={headerRef}>
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
          <div className="flex min-w-0 flex-1 basis-full items-center gap-3 sm:basis-auto">
            <h2 className="min-w-0 truncate text-lg font-semibold text-platforma-ink" title={bot.name}>{bot.name}</h2>
            <Badge size="sm" variant="neutral">{t(`aiScenario.${bot.scenario || "inbox"}`)}</Badge>
            <Badge size="sm" variant={statusVariant(bot.status, runtimeBlocked)}>{statusLabel}</Badge>
          </div>

          <div className="flex shrink-0 flex-wrap items-center gap-2">
            {bot.scenario !== "crm" && <Button type="button" size="sm" className="min-h-11 sm:min-h-9" variant="secondary" onClick={onOpenMessages}>
              <MessageSquareText aria-hidden="true" size={16} />
              {t("aiAgents.openMessages")}
            </Button>}
            <div className="flex min-h-11 items-center gap-2 sm:min-h-9">
              <Switch
                checked={bot.status === "active"}
                disabled={!canManage || activationBlocked || (dirty && bot.status !== "active")}
                isLoading={isSaving}
                label={t("aiAgents.statusSwitch", { name: bot.name })}
                onChange={onToggleStatus}
                size="dense"
                tone="ai"
                title={activationBlocked ? t("aiAgents.activationBlocked") : undefined}
              />
            </div>
          </div>
        </div>

        <Tabs
          ariaLabel={t("aiAgents.editorTabsAria")}
          idPrefix="ai-agent-editor"
          className="mt-4 [&_[role=tab]]:min-h-11 sm:[&_[role=tab]]:min-h-10"
          tone="ai"
          appearance="underline"
          value={activeSection}
          onChange={onSectionChange}
          options={sections.map((section) => ({
            value: section.id,
            label: t(section.labelKey),
          }))}
        />
      </header>

      <div
        id={`ai-agent-editor-panel-${activeSection}`}
        role="tabpanel"
        aria-labelledby={`ai-agent-editor-tab-${activeSection}`}
        className="min-w-0 py-5"
      >
        <fieldset disabled={isSaving} className="min-w-0 w-full">{children}</fieldset>
      </div>

      {canManage && (showFooter || nextSection) ? (
        <footer className="flex flex-wrap items-center justify-end gap-x-3 gap-y-2 border-t border-platforma-border pt-4">
          <p className="mr-auto text-xs font-medium text-platforma-subtle" aria-live="polite">
            {dirty
              ? t("aiAgents.unsavedIndicator")
              : saveState === "saved"
                ? t("aiAgents.savedIndicator")
                : ""}
          </p>
          <div className="flex flex-wrap justify-end gap-2">
            {showFooter ? <><Button type="button" className="min-h-11 sm:min-h-10" variant="secondary" disabled={!dirty || isSaving} onClick={onReset}>
              {t("common.cancel")}
            </Button>
            <Button type="button" className="min-h-11 sm:min-h-10" disabled={!dirty || saveDisabled} isLoading={isSaving} onClick={onSave}>
              {t("aiAgents.saveChanges")}
            </Button></> : null}
            {nextSection ? <Button type="button" className="min-h-11 sm:min-h-10" variant="secondary" disabled={isSaving} onClick={() => onSectionChange(nextSection.id)}>{t("aiSetup.next", { section: t(nextSection.labelKey) })}</Button> : null}
          </div>
        </footer>
      ) : null}
      {afterFooter}
    </section>
  );
}

import { useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { ArrowLeft, CheckCheck, PauseCircle, PlayCircle, UserCheck } from "lucide-react";
import type { InboxConversation } from "../../../api/inbox";
import type { ActionMenuItem } from "../../../components/ui/ActionMenu";
import { Button } from "../../../components/ui/Button";
import type { Translate } from "../conversationTypes";
import { channelLabel, conversationTitle } from "../conversationUtils";
import { InboxMemoryControl } from "./InboxMemoryControl";
import { Pill, Tooltip } from "./ConversationPrimitives";

type Props = {
  selected: InboxConversation;
  headerActions?: ReactNode;
  threadMenu: ActionMenuItem[];
  canUpdate: boolean;
  canToggleBot: boolean;
  onMobileClose: () => void;
  onAssign: () => void;
  assignPending: boolean;
  onToggleBot: () => void;
  toggleBotPending: boolean;
  onCloseConversation: () => void;
  closePending: boolean;
  onReopenConversation: () => void;
  reopenPending: boolean;
  t: Translate;
};

export function ConversationThreadHeader({ selected, headerActions, threadMenu, canUpdate, canToggleBot, onMobileClose, onAssign, assignPending, onToggleBot, toggleBotPending, onCloseConversation, closePending, onReopenConversation, reopenPending, t }: Props) {
  const headerRef = useRef<HTMLDivElement>(null);
  const [compact, setCompact] = useState(true);
  useLayoutEffect(() => {
    const header = headerRef.current;
    if (!header) return;
    const observer = new ResizeObserver(([entry]) => setCompact(entry.contentRect.width < 760));
    observer.observe(header);
    return () => observer.disconnect();
  }, []);
  const botLabel = t(selected.bot_enabled ? "conversations.pauseBot" : "conversations.enableBot");
  const botDisabled = !canToggleBot || toggleBotPending || selected.status !== "open" || (!selected.bot_enabled && selected.ai_safety?.calls_remaining === 0);
  const closed = selected.status === "closed";
  const lifecycleLabel = t(closed ? "conversations.openDialog" : "conversations.closeDialog");
  const lifecyclePending = closed ? reopenPending : closePending;
  const lifecycleAction = closed ? onReopenConversation : onCloseConversation;
  const menuItems: ActionMenuItem[] = [
    ...(compact ? [
      { key: "assign", label: t("conversations.takeDialog"), icon: UserCheck, disabled: !canUpdate || assignPending, onSelect: onAssign },
      { key: "toggle-bot", label: botLabel, icon: selected.bot_enabled ? PauseCircle : PlayCircle, disabled: botDisabled, onSelect: onToggleBot },
      { key: "lifecycle", label: lifecycleLabel, icon: closed ? PlayCircle : CheckCheck, disabled: !canUpdate || lifecyclePending, onSelect: lifecycleAction },
    ] : []),
    ...threadMenu,
  ];
  return (
    <div ref={headerRef} data-testid="inbox-thread-header" className="flex min-h-[72px] shrink-0 items-center gap-2 border-b border-platforma-border bg-platforma-card px-3 py-3 lg:px-4">
      <Button variant="ghost" size="icon" className="h-11 w-11 shrink-0 lg:hidden" aria-label={t("common.close")} onClick={onMobileClose}><ArrowLeft size={18} /></Button>
      <div className="min-w-0 flex-1">
        <h2 title={conversationTitle(selected, t)} className="truncate text-base font-bold leading-6 text-platforma-text">{conversationTitle(selected, t)}</h2>
        <div className="mt-1 flex min-w-0 items-center gap-1.5 text-xs leading-4 text-platforma-subtle">
          <span className="shrink-0">{channelLabel(selected.channel, t)}</span>
          {compact ? <span className="truncate">· {t(selected.bot_enabled ? "conversations.botActive" : "conversations.botPaused")}</span> : null}
          {selected.assigned_to_email ? <span title={selected.assigned_to_email} className="truncate">· {selected.assigned_to_email}</span> : null}
        </div>
        {selected.handoff_required ? <Pill className="mt-1 bg-[var(--platforma-warning-soft)] text-platforma-warning ring-platforma-warning/20">{t("conversations.needsOperator")}</Pill> : null}
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {!compact ? <>
          <Tooltip label={t("conversations.assignTooltip")}><Button data-conversation-action-id="assign" variant="secondary" size="sm" className="whitespace-nowrap" disabled={!canUpdate} isLoading={assignPending} onClick={onAssign} aria-label={t("conversations.takeDialog")}><UserCheck size={16} />{t("conversations.takeDialog")}</Button></Tooltip>
          <Tooltip label={botLabel}><Button data-conversation-action-id="toggle-bot" variant={selected.bot_enabled ? "warning" : "secondary"} size="sm" className="whitespace-nowrap" disabled={botDisabled} isLoading={toggleBotPending} onClick={onToggleBot} aria-label={botLabel}>
            {selected.bot_enabled ? <PauseCircle size={16} /> : <PlayCircle size={16} />}
            {t(selected.bot_enabled ? "conversations.botActive" : "conversations.botPaused")}
          </Button></Tooltip>
          <Tooltip label={lifecycleLabel}><Button data-conversation-action-id={closed ? "reopen" : "close"} variant="secondary" size="sm" className="whitespace-nowrap" disabled={!canUpdate} isLoading={lifecyclePending} onClick={lifecycleAction} aria-label={lifecycleLabel}>{closed ? <PlayCircle size={16} /> : <CheckCheck size={16} />}{t(closed ? "common.open" : "common.close")}</Button></Tooltip>
        </> : null}
        {headerActions}
        <InboxMemoryControl key={selected.id} conversation={selected} items={menuItems} />
      </div>
    </div>
  );
}

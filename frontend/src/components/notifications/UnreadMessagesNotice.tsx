import { MessageSquareText, X } from "lucide-react";
import { useEffect, useLayoutEffect, useRef, useState } from "react";

import { useI18n } from "../../lib/i18n";
import { Button } from "../ui/Button";
import { StatusNotice } from "../ui/StatusNotice";
import { restoreNoticeFocus } from "./NotificationHost";

export function UnreadMessagesNotice({ count, onOpen, onDismiss, onPauseChange }: {
  count: number;
  onOpen: () => void;
  onDismiss: () => void;
  onPauseChange?: (paused: boolean) => void;
}) {
  const { t } = useI18n();
  const card = useRef<HTMLDivElement>(null);
  const opener = useRef(document.activeElement instanceof HTMLElement ? document.activeElement : null);
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  useEffect(() => { onPauseChange?.(hovered || focused); }, [hovered, focused, onPauseChange]);
  useEffect(() => () => onPauseChange?.(false), [onPauseChange]);
  useLayoutEffect(() => {
    const node = card.current;
    return () => restoreNoticeFocus(node, opener.current);
  }, []);
  return <div ref={card} onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)}
    onFocusCapture={() => setFocused(true)} onBlurCapture={event => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setFocused(false); }}><StatusNotice
    tone="info"
    role="status"
    ariaLive="polite"
    icon={MessageSquareText}
    actionPlacement="corner"
    title={t("header.chatToastTitle")}
    description={t("header.chatToastText", { count: count > 99 ? "99+" : count })}
    dismiss={<button
      type="button"
      className="platforma-notice-close"
      onClick={() => { restoreNoticeFocus(card.current, opener.current); onDismiss(); }}
      aria-label={t("common.close")}
    ><X aria-hidden="true" size={17} /></button>}
    details={<div className="flex justify-center"><Button size="sm" onClick={onOpen}>{t("header.openMessages")}</Button></div>}
  /></div>;
}

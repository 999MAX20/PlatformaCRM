import { MessageSquareText, X } from "lucide-react";

import { useI18n } from "../../lib/i18n";
import { Button } from "../ui/Button";
import { StatusNotice } from "../ui/StatusNotice";

export function UnreadMessagesNotice({ count, onOpen, onDismiss }: {
  count: number;
  onOpen: () => void;
  onDismiss: () => void;
}) {
  const { t } = useI18n();
  return <StatusNotice
    tone="danger"
    role="status"
    ariaLive="polite"
    icon={MessageSquareText}
    actionPlacement="corner"
    title={t("header.chatToastTitle")}
    description={t("header.chatToastText", { count: count > 99 ? "99+" : count })}
    action={<button
      type="button"
      className="platforma-focus-ring grid h-8 w-8 shrink-0 place-items-center rounded-control text-platforma-faint transition hover:bg-surface-hover hover:text-platforma-text"
      onClick={onDismiss}
      aria-label={t("common.close")}
    ><X size={17} /></button>}
    details={<div className="flex justify-center"><Button size="sm" onClick={onOpen}>{t("header.openMessages")}</Button></div>}
  />;
}

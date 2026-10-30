import { useInboxQueries } from "./useInboxQueries";
import { useInboxFilterOptions } from "./useInboxFilterOptions";

import { Link } from "react-router";

import { Button } from "../../components/ui/Button";

import { Dialog } from "../../components/ui/Overlay";

import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "../../components/ui/StateViews";

import { useI18n } from "../../lib/i18n";
import { hasPermission } from "../../lib/permissions";

import { useAuth } from "../auth/AuthProvider";

import { channelLabel } from "./conversationUtils";

import type { Dispatch, SetStateAction } from "react";
type Props = {
  t: ReturnType<typeof useI18n>["t"];
  quickRepliesOpen: boolean;
  setQuickRepliesOpen: Dispatch<SetStateAction<boolean>>;
  quickReplySearch: string;
  setQuickReplySearch: Dispatch<SetStateAction<string>>;
  quickReplies: ReturnType<typeof useInboxQueries>["quickReplies"];
  quickReplyTemplates: ReturnType<
    typeof useInboxFilterOptions
  >["quickReplyTemplates"];
  selected: ReturnType<typeof useInboxQueries>["selected"];
  businessId: number;
  user: ReturnType<typeof useAuth>["user"];
  insertQuickReply: (text: string) => void;
};
export function InboxQuickRepliesDialog({
  t,
  quickRepliesOpen,
  setQuickRepliesOpen,
  quickReplySearch,
  setQuickReplySearch,
  quickReplies,
  quickReplyTemplates,
  selected,
  businessId,
  user,
  insertQuickReply,
}: Props) {
  return (
    <Dialog
      title={t("conversations.quickRepliesTitle")}
      open={quickRepliesOpen}
      focusReturnId="inbox-quick-replies"
      onClose={() => setQuickRepliesOpen(false)}
      size="md"
      bodyClassName="bg-platforma-card p-0"
    >
      <div className="border-b border-platforma-border p-4">
        <input
          type="search"
          className="h-11 w-full rounded-control border border-platforma-border bg-platforma-card px-3 text-sm font-semibold text-platforma-text outline-hidden transition placeholder:text-platforma-muted focus-visible:border-brand-400 focus-visible:ring-4 focus-visible:ring-brand-100"
          placeholder={t("conversations.quickRepliesSearch")}
          value={quickReplySearch}
          onChange={(event) => setQuickReplySearch(event.target.value)}
          autoFocus
        />
      </div>
      <div className="max-h-[56vh] overflow-y-auto p-3">
        {quickReplies.isError ? (
          <ErrorState
            error={quickReplies.error}
            action={
              <Button
                variant="secondary"
                onClick={() => void quickReplies.refetch()}
              >
                {t("common.retry")}
              </Button>
            }
          />
        ) : null}
        {quickReplies.isLoading ? <LoadingState /> : null}
        {!quickReplies.isLoading &&
        !quickReplies.isError &&
        !quickReplyTemplates.length ? (
          <EmptyState
            title={t("conversations.noTemplates")}
            description={t(
              quickReplySearch.trim()
                ? "settings.redesign.noMatches"
                : "conversations.noQuickRepliesText",
            )}
            action={
              !quickReplySearch.trim() &&
              String(selected?.business || businessId) === String(businessId) &&
              hasPermission(user, businessId, "conversations", "manage") ? (
                <Link
                  to="/app/settings#quick-replies"
                  className="platforma-focus-ring inline-flex min-h-11 items-center rounded-control px-3 text-sm font-semibold text-brand-700 underline underline-offset-4"
                >
                  {t("settings.workflow.createQuickReply")}
                </Link>
              ) : undefined
            }
          />
        ) : null}
        <div className="space-y-2">
          {quickReplyTemplates.map((template) => (
            <button
              key={template.id}
              type="button"
              className="w-full rounded-card border border-platforma-border bg-platforma-card p-3 text-left transition hover:border-brand-200 hover:bg-brand-50/40"
              onClick={() => insertQuickReply(template.text)}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-bold text-platforma-text">
                    {template.title}
                  </p>
                  <p className="mt-1 line-clamp-3 text-sm font-semibold leading-6 text-platforma-muted">
                    {template.text}
                  </p>
                </div>
                <span className="shrink-0 rounded-full bg-surface-muted px-2 py-1 text-[11px] font-bold text-platforma-muted">
                  {template.channel === "all"
                    ? t("conversations.allChannels")
                    : channelLabel(template.channel, t)}
                </span>
              </div>
              {template.category ? (
                <p className="mt-2 text-xs font-bold uppercase tracking-[0.12em] text-platforma-muted">
                  {template.category}
                </p>
              ) : null}
            </button>
          ))}
        </div>
      </div>
    </Dialog>
  );
}

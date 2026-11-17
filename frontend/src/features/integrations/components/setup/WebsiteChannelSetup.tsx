import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { Button } from "../../../../components/ui/Button";
import { ErrorState } from "../../../../components/ui/StateViews";
import { useI18n } from "../../../../lib/i18n";
import type { BotChannel } from "../../../../types";
import { channelConnectionState } from "../../channelConnectionState";
import { MessengerSetupShell, SetupInstructions } from "./IntegrationSetupUi";

export function WebsiteChannelSetup({ channel, canManage, pending, error, onToggle }: {
  channel?: BotChannel; canManage: boolean; pending: boolean; error: Error | null;
  onToggle: (channel: BotChannel, status: BotChannel["status"]) => void;
}) {
  const { t } = useI18n();
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState(false);
  const state = channelConnectionState(channel);
  if (!channel) return <ErrorState message={t("aiAgents.channelSetupUnavailable")} />;
  const apiBase = new URL(import.meta.env.VITE_API_URL || window.location.origin, window.location.origin);
  const scriptUrl = new URL("/widget/platformacrm-widget.js", window.location.origin);
  const localOnly = [apiBase, scriptUrl].some(url => ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname));
  const snippet = `<script src="${scriptUrl.href}" data-platforma-token="${channel.public_token}" data-platforma-api="${apiBase.href.replace(/\/$/, "")}"></script>`;
  const copy = async () => {
    setCopyError(false);
    try { await navigator.clipboard.writeText(snippet); setCopied(true); }
    catch { setCopied(false); setCopyError(true); }
  };
  return <MessengerSetupShell title={t("aiAgents.channel.website")}
    description={t("integrations.setup.websiteDescription")} status={t(state.key)} statusTone={state.tone}
    canManage={canManage} inboxChannel="website" channelToggleVisible={["active", "paused"].includes(channel.status)} channelEnabled={channel.status === "active"}
    channelToggleLoading={pending} onToggleChannel={value => onToggle(channel, value ? "active" : "paused")}
    instructions={channel.status !== "active" ? <SetupInstructions steps={[t("integrations.setup.websiteStep1"), t("integrations.setup.websiteStep2"), t("integrations.setup.websiteStep3")]} /> : null}
    actions={channel.status !== "active" ? <Button type="button" disabled={!canManage || pending} isLoading={pending}
      onClick={() => onToggle(channel, "active")}>{t("aiAgents.connect")}</Button> : null}
    error={error ? <ErrorState error={error} /> : null}>
    <div className="min-w-0 space-y-3">
      <div className="space-y-2">
        <p className="text-sm font-semibold text-platforma-text">{t("integrations.setup.widgetCode")}</p>
        <div className="flex items-start rounded-control border border-platforma-control bg-surface-muted">
          <pre tabIndex={0} aria-label={t("integrations.setup.installCode")} className="platforma-focus-ring min-w-0 flex-1 whitespace-pre-wrap break-all p-3 text-xs leading-5 text-platforma-text">{snippet}</pre>
          <Button type="button" variant="ghost" className="my-1 mr-1 min-h-11 min-w-11 shrink-0 px-2" aria-label={t("integrations.website.copySnippet")} onClick={() => void copy()}>
            {copied ? <Check size={20} aria-hidden="true" /> : <Copy size={20} aria-hidden="true" />}
          </Button>
        </div>
        <p className="text-sm text-platforma-subtle">{t("integrations.setup.copyToWebsite")}</p>
      </div>
      {localOnly && <p role="status" className="text-sm text-platforma-subtle">{t("integrations.setup.localWebsite")}</p>}
      <span role="status" className={copied ? "block text-sm text-platforma-subtle" : "sr-only"}>{copied ? t("integrations.setup.copied") : ""}</span>
      {copyError && <p role="alert" className="text-sm text-platforma-danger">{t("integrations.setup.copyFailed")}</p>}
      {channel.status === "active" ? <p className="text-sm text-platforma-subtle">{t("integrations.setup.websiteTest")}</p> : null}
    </div>
  </MessengerSetupShell>;
}

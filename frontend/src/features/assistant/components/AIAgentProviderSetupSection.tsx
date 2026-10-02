import { useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { botChannelsApi } from "../../../api/bots";
import { Button } from "../../../components/ui/Button";
import { Modal } from "../../../components/ui/Modal";
import { ToggleSwitch } from "../../../components/ui/Switch";
import { useI18n } from "../../../lib/i18n";
import { cn } from "../../../lib/cn";
import type { Bot as BotType, BotChannel, Id } from "../../../types";
import { InstagramInlineSetup } from "../../integrations/components/setup/InstagramSetup";
import { LogoMark } from "../../integrations/components/setup/IntegrationSetupUi";
import { TelegramInlineSetup } from "../../integrations/components/setup/TelegramSetup";
import { WhatsAppInlineSetup } from "../../integrations/components/setup/WhatsAppSetup";
import { channelStatus, channelStatusClass } from "../aiAgentsUtils";
import { FieldHint } from "./AIAgentsShared";
export function ChannelManagerSection(props: {
  businessId: Id;
  bot: BotType;
  canManage: boolean;
  channelByName: (name: BotChannel["channel"]) => BotChannel | undefined;
  addChannel: ReturnType<typeof useMutation<BotChannel, Error, { botId: number; channel: BotChannel["channel"] }>>;
  toggleChannel: ReturnType<typeof useMutation<BotChannel, Error, { channel: BotChannel; status: BotChannel["status"] }>>;
}) {
  const { t } = useI18n();
  const hasAnyChannel = (["website", "telegram", "whatsapp", "instagram"] as const)
    .some((channel) => props.channelByName(channel));
  return (
    <section className="space-y-3">
      <h3 className="text-base font-semibold text-platforma-ink">{t("aiAgents.channelsTitle")}</h3>
      <ChannelsSection {...props} />
      {!hasAnyChannel ? (
        <details className="border-t border-platforma-border pt-2 text-sm text-platforma-subtle">
          <summary className="platforma-focus-ring min-h-11 cursor-pointer py-2 font-semibold">{t("aiAgents.onboarding.channels.helpTitle")}</summary>
          <p className="pb-2 leading-5">{t("aiAgents.onboarding.channels.helpText")}</p>
          <p className="pb-2 leading-5">{t("aiAgents.onboarding.channels.recommendation")}</p>
        </details>
      ) : null}
    </section>
  );
}

function ChannelsSection({
  businessId,
  bot,
  canManage,
  channelByName,
  addChannel,
  toggleChannel,
}: {
  businessId: Id;
  bot: BotType;
  canManage: boolean;
  channelByName: (name: BotChannel["channel"]) => BotChannel | undefined;
  addChannel: ReturnType<typeof useMutation<BotChannel, Error, { botId: number; channel: BotChannel["channel"] }>>;
  toggleChannel: ReturnType<typeof useMutation<BotChannel, Error, { channel: BotChannel; status: BotChannel["status"] }>>;
}) {
  const { t } = useI18n();
  const [setupChannel, setSetupChannel] = useState<BotChannel["channel"] | null>(null);
  const [createdChannel, setCreatedChannel] = useState<BotChannel | null>(null);
  const [connectingChannel, setConnectingChannel] = useState<BotChannel["channel"] | null>(null);
  const channelCards: Array<{ key: BotChannel["channel"]; title: string; description: string; logo?: string }> = [
    { key: "website", title: t("aiAgents.channel.website"), description: t("aiAgents.channel.websiteText") },
    { key: "telegram", title: "Telegram", description: t("aiAgents.channel.telegramText"), logo: "/integrations_logos/telegram.png" },
    { key: "whatsapp", title: "WhatsApp", description: t("aiAgents.channel.whatsappText"), logo: "/integrations_logos/whatsapp.png" },
    { key: "instagram", title: "Instagram", description: t("aiAgents.channel.instagramText"), logo: "/integrations_logos/instagram.png" },
  ];
  const activeChannel = setupChannel
    ? channelByName(setupChannel) || (createdChannel?.channel === setupChannel ? createdChannel : undefined)
    : undefined;

  return (
    <>
      <div>
        <div className="hidden grid-cols-[minmax(0,1fr)_145px_180px] gap-3 border-b border-platforma-border bg-surface-muted px-3 py-2 text-xs font-semibold text-platforma-subtle sm:grid">
          <span>{t("conversations.channel")}</span><span>{t("aiAgents.statusLabel")}</span><span>{t("aiAgents.section.actions")}</span>
        </div>
        {channelCards.map((item) => {
          const channel = channelByName(item.key);
          const connected = channel?.status === "active";
          return (
            <article key={item.key} className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-3 border-b border-platforma-border px-1 py-3 sm:grid-cols-[minmax(0,1fr)_145px_180px] sm:px-3">
              <div className="flex min-w-0 items-start gap-3">
                <LogoMark compact logo={item.logo} label={item.title} />
                <div className="min-w-0">
                  <h4 className="text-sm font-semibold text-platforma-ink">{item.title}</h4>
                  <details className="mt-1 text-sm leading-5 text-platforma-subtle">
                    <summary className="platforma-focus-ring cursor-pointer py-1">{item.description}</summary>
                    <FieldHint>{t(`aiAgents.hint.channel.${item.key}`)}</FieldHint>
                  </details>
                </div>
              </div>
              <span className={cn("mt-1 w-fit rounded-full px-2 py-0.5 text-xs font-semibold ring-1", channelStatusClass(channel))}>
                {channelStatus(channel, t)}
              </span>
              <div className="col-span-2 flex min-h-10 items-center gap-2 sm:col-span-1">
                  <Button
                    type="button"
                    className="min-h-11 min-w-[120px] sm:min-h-10"
                    variant={channel ? "secondary" : "primary"}
                    data-focus-return-id={`ai-agent-channel-${bot.id}-${item.key}`}
                    disabled={!canManage || addChannel.isPending}
                    isLoading={addChannel.isPending && connectingChannel === item.key}
                    onClick={() => {
                      if (!channel) {
                        setConnectingChannel(item.key);
                        addChannel.mutate({ botId: Number(bot.id), channel: item.key }, {
                          onSuccess: (created) => {
                            setCreatedChannel(created);
                            setSetupChannel(item.key);
                          },
                          onSettled: () => setConnectingChannel(null),
                        });
                        return;
                      }
                      setCreatedChannel(null);
                      setSetupChannel(item.key);
                    }}
                  >
                    {channel ? t("aiAgents.configure") : t("aiAgents.connect")}
                  </Button>
                  {channel && ["active", "paused"].includes(channel.status) ? (
                    <ToggleSwitch
                      checked={connected}
                      disabled={!canManage}
                      isLoading={toggleChannel.isPending}
                      label={`${item.title}: ${connected ? t("aiAgents.disable") : t("aiAgents.enable")}`}
                      tone="ai"
                      onChange={(checked) => toggleChannel.mutate({ channel, status: checked ? "active" : "paused" })}
                    />
                  ) : null}
              </div>
            </article>
          );
        })}
      </div>

      <Modal
        title={setupChannel ? t("aiAgents.connectionTitle", { title: channelCards.find((item) => item.key === setupChannel)?.title || "" }) : t("aiAgents.connection")}
        open={Boolean(setupChannel)}
        onClose={() => { setSetupChannel(null); setCreatedChannel(null); }}
        focusReturnId={setupChannel ? `ai-agent-channel-${bot.id}-${setupChannel}` : undefined}
      >
        {setupChannel === "telegram" ? (
          <TelegramInlineSetup canManage={canManage} channel={activeChannel} />
        ) : setupChannel === "whatsapp" ? (
          <WhatsAppInlineSetup businessId={businessId} canManage={canManage} channel={activeChannel} />
        ) : setupChannel === "instagram" ? (
          <InstagramInlineSetup businessId={businessId} canManage={canManage} channel={activeChannel} />
        ) : setupChannel === "website" ? (
          <WebsiteSetup bot={bot} channel={activeChannel} />
        ) : null}
      </Modal>
    </>
  );
}

function WebsiteSetup({ bot, channel }: { bot: BotType; channel?: BotChannel }) {
  const { t } = useI18n();
  const widgetApiBase = import.meta.env.VITE_API_URL || window.location.origin;
  const snippet = channel ? `<script src=\"/widget/platformacrm-widget.js\" data-platforma-token=\"${channel.public_token}\" data-platforma-api=\"${widgetApiBase}\"></script>` : "";
  return (
    <div className="space-y-4">
      <div className="border-b border-platforma-border pb-3">
        <h3 className="text-base font-semibold text-midnight">{t("aiAgents.websiteSetupTitle")}</h3>
        <p className="mt-1 text-sm font-semibold leading-6 text-platforma-faint">
          {t("aiAgents.websiteSetupText", { name: bot.name })}
        </p>
      </div>
      {channel ? (
        <pre className="max-h-56 overflow-auto rounded-2xl bg-platforma-ink p-4 text-xs font-semibold leading-6 text-white">{snippet}</pre>
      ) : (
        <div className="rounded-2xl border border-dashed border-platforma-border bg-surface-muted p-4 text-sm font-semibold text-platforma-faint">
          {t("aiAgents.websiteSetupEmpty")}
        </div>
      )}
    </div>
  );
}

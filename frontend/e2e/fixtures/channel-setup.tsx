import React from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BrowserRouter } from "react-router";
import { I18nProvider } from "../../src/lib/i18n";
import { NotificationProvider } from "../../src/components/notifications/NotificationProvider";
import { ChannelManagerSection } from "../../src/features/assistant/components/AIAgentProviderSetupSection";
import { botChannelsApi, ensureBotChannel } from "../../src/api/bots";
import type { Bot, BotChannel } from "../../src/types";
import "../../src/lib/focusModality";
import "@fontsource-variable/manrope";
import "@fontsource-variable/noto-sans";
import "../../src/styles.css";

function Fixture() {
  const client = useQueryClient();
  const channels = useQuery({ queryKey: ["bot-channels"], queryFn: () => botChannelsApi.list({ bot: 9 }) });
  const refresh = () => client.invalidateQueries({ queryKey: ["bot-channels"] });
  const addChannel = useMutation<BotChannel, Error, { botId: number; channel: BotChannel["channel"] }>({ mutationFn: ensureBotChannel, onSuccess: refresh });
  const toggleChannel = useMutation<BotChannel, Error, { channel: BotChannel; status: BotChannel["status"] }>({ mutationFn: ({ channel, status }) => botChannelsApi.update({ id: channel.id, payload: { status } }), onSuccess: refresh });
  return <main className="mx-auto max-w-5xl p-4">
    <ChannelManagerSection businessId={7} bot={{ id: 9, name: "Verification", scenario: "inbox" } as Bot}
      canManage={!location.search.includes("readonly")} channelByName={name => channels.data?.find(channel => channel.channel === name)}
      addChannel={addChannel} toggleChannel={toggleChannel} />
  </main>;
}
createRoot(document.getElementById("root")!).render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
  <BrowserRouter><I18nProvider><NotificationProvider><Fixture /></NotificationProvider></I18nProvider></BrowserRouter>
</QueryClientProvider>);

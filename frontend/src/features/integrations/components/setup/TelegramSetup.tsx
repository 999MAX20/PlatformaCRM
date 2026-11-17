import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { botChannelsApi, telegramChannelApi } from "../../../../api/bots";
import { Button } from "../../../../components/ui/Button";
import { ErrorState } from "../../../../components/ui/StateViews";
import { CredentialInput } from "./CredentialInput";
import { channelConnectionState } from "../../channelConnectionState";
import { useNotification } from "../../../../components/notifications/NotificationProvider";
import { useI18n } from "../../../../lib/i18n";
import type { BotChannel } from "../../../../types";
import { merchantSafeIntegrationError } from "../../utils";
import { MessengerSetupShell, SetupInstructions } from "./IntegrationSetupUi";

export function TelegramInlineSetup({
  canManage,
  channel,
}: {
  canManage: boolean;
  channel?: BotChannel;
}) {
  const { t } = useI18n();
  const showNotification = useNotification();
  const queryClient = useQueryClient();
  const [botToken, setBotToken] = useState("");
  const [replacingToken, setReplacingToken] = useState(false);
  const [checkFailure, setCheckFailure] = useState<string | null>(null);

  function setNotice(message: string | null, tone: "success" | "info" | "warning" | "danger" = "success") {
    if (!message) return;
    showNotification({ message, tone });
  }

  const status = useQuery({
    queryKey: ["telegram-status", channel?.id],
    queryFn: () => telegramChannelApi.status(Number(channel?.id)),
    enabled: Boolean(channel?.id),
  });

  const saveToken = useMutation({
    mutationFn: () => telegramChannelApi.configure({ channelId: Number(channel?.id), botToken }),
    onSuccess: () => {
      setBotToken("");
      setReplacingToken(false);
      setCheckFailure(null);
      setNotice(t("integrations.telegram.tokenSavedNotice"));
      queryClient.invalidateQueries({ queryKey: ["bot-channels"] });
      queryClient.invalidateQueries({ queryKey: ["telegram-status", channel?.id] });
      queryClient.invalidateQueries({ queryKey: ["business-connectors"] });
    },
  });

  const testConnection = useMutation({
    mutationFn: () => telegramChannelApi.testConnection(Number(channel?.id)),
    onSuccess: (data) => {
      setCheckFailure(data.ok ? null : data.reason || "");
      setNotice(data.ok ? t("integrations.telegram.connectionChecked") : merchantSafeIntegrationError(data.reason, t, canManage), data.ok ? "success" : "warning");
      queryClient.invalidateQueries({ queryKey: ["bot-channels"] });
      queryClient.invalidateQueries({ queryKey: ["telegram-status", channel?.id] });
      queryClient.invalidateQueries({ queryKey: ["business-connectors"] });
    },
  });

  const setWebhook = useMutation({
    mutationFn: async () => {
      const current = status.data || await telegramChannelApi.status(Number(channel?.id));
      return telegramChannelApi.setWebhook({ channelId: Number(channel?.id), webhookUrl: current.webhook_url });
    },
    onSuccess: (data) => {
      setCheckFailure(data.ok ? null : data.reason || "");
      setNotice(data.ok ? t("integrations.telegram.inboundConnected") : merchantSafeIntegrationError(data.reason, t, canManage), data.ok ? "success" : "warning");
      queryClient.invalidateQueries({ queryKey: ["bot-channels"] });
      queryClient.invalidateQueries({ queryKey: ["telegram-status", channel?.id] });
      queryClient.invalidateQueries({ queryKey: ["integration-event-logs"] });
      queryClient.invalidateQueries({ queryKey: ["business-connectors"] });
    },
  });
  const toggleChannel = useMutation({
    mutationFn: (nextStatus: BotChannel["status"]) => {
      if (!channel) throw new Error("Channel is required.");
      return botChannelsApi.update({ id: channel.id, payload: { status: nextStatus } });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bot-channels"] });
      queryClient.invalidateQueries({ queryKey: ["business-connectors"] });
    },
  });

  const error = saveToken.error || testConnection.error || setWebhook.error || toggleChannel.error || status.error;
  const providerFailure = checkFailure ?? (status.data?.status === "error" ? status.data.last_error : null);
  const tokenConfigured = Boolean(status.data?.token_configured);
  const tokenVerified = Boolean(status.data?.token_verified);
  const webhookConfigured = Boolean(status.data?.webhook_configured);
  const canSaveToken = /^\d+:[A-Za-z0-9_-]+$/.test(botToken.trim());
  const connection = channelConnectionState(channel);
  const busy = saveToken.isPending || testConnection.isPending || setWebhook.isPending || toggleChannel.isPending;

  if (!channel) {
    return <ErrorState message={t("aiAgents.channelSetupUnavailable")} />;
  }

  return (
    <MessengerSetupShell
      logo="/integrations_logos/telegram.png"
      title="Telegram"
      description={t("integrations.setup.telegramDescription")}
      status={t(connection.key)}
      statusTone={connection.tone}
      loading={status.isPending}
      error={error || providerFailure != null ? <ErrorState message={merchantSafeIntegrationError(error || providerFailure, t, canManage)} action={status.isError ? <Button type="button" onClick={() => void status.refetch()}>{t("common.retry")}</Button> : undefined} /> : null}
      canManage={canManage && !busy && !status.isError}
      inboxChannel="telegram"
      channelToggleVisible={webhookConfigured}
      channelEnabled={channel.status === "active"}
      channelToggleLoading={toggleChannel.isPending}
      onToggleChannel={(checked) => toggleChannel.mutate(checked ? "active" : "paused")}
      instructions={!status.isError && (!webhookConfigured || replacingToken) ? <SetupInstructions
        steps={[t("integrations.setup.telegramStep1"), t("integrations.setup.telegramStep2"), t("integrations.setup.telegramStep3")]}
        note={tokenConfigured && !webhookConfigured ? t("integrations.setup.telegramFinish") : undefined} /> : null}
      actions={!status.isError ? <>
        {webhookConfigured && !replacingToken ? <>
          <Button type="button" variant="secondary" disabled={!canManage || busy} onClick={() => setReplacingToken(true)}>{t("integrations.setup.replaceKey")}</Button>
          <Button type="button" variant="secondary" disabled={!canManage || busy} isLoading={testConnection.isPending} onClick={() => testConnection.mutate()}>{t("integrations.telegram.testConnection")}</Button>
        </> : <>
          {replacingToken ? <Button type="button" variant="ghost" disabled={busy} onClick={() => { setBotToken(""); setReplacingToken(false); }}>{t("common.cancel")}</Button> : null}
          {botToken || !tokenConfigured || replacingToken ? <Button type="button" disabled={!canManage || busy || !canSaveToken} isLoading={saveToken.isPending} onClick={() => saveToken.mutate()}>
            {replacingToken ? t("integrations.telegram.saveKey") : t("aiAgents.connect")}
          </Button> : !tokenVerified ? <Button type="button" disabled={!canManage || busy} isLoading={testConnection.isPending} onClick={() => testConnection.mutate()}>
            {t("integrations.telegram.testConnection")}
          </Button> : <Button type="button" disabled={!canManage || busy || status.isFetching} isLoading={setWebhook.isPending} onClick={() => setWebhook.mutate()}>
            {t("integrations.telegram.connectInbound")}
          </Button>}
        </>}
      </> : null}
    >
      {!status.isError && <>
      {!webhookConfigured || replacingToken ? (
        <div className="space-y-2">
          <CredentialInput
            label={t("integrations.telegram.botKey")}
            aria-label={t("integrations.telegram.botKey")}
            revealable
            value={botToken}
            onChange={(event) => setBotToken(event.target.value)}
            placeholder={tokenConfigured ? t("integrations.telegram.tokenReplacePlaceholder") : t("integrations.setup.telegramPlaceholder")}
            disabled={!canManage || busy}
          />
          <p className="text-sm leading-5 text-platforma-subtle">{tokenConfigured ? t("integrations.telegram.tokenSavedPrivate") : t("integrations.setup.keyPrivate")}</p>
          {botToken && !canSaveToken && <p role="alert" className="mt-2 text-sm text-platforma-danger">{t("integrations.setup.invalidTelegramKey")}</p>}
        </div>
      ) : null}
      </>}
    </MessengerSetupShell>
  );
}

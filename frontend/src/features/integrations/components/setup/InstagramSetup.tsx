import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, ShieldCheck } from "lucide-react";

import { botChannelsApi, instagramChannelApi } from "../../../../api/bots";
import { businessConnectorsApi } from "../../../../api/connectors";
import { Button } from "../../../../components/ui/Button";
import { ErrorState } from "../../../../components/ui/StateViews";
import { Input } from "../../../../components/ui/Input";
import { useNotification } from "../../../../components/notifications/NotificationProvider";
import { useI18n } from "../../../../lib/i18n";
import type { BotChannel, Id } from "../../../../types";
import { merchantSafeIntegrationError } from "../../utils";
import { AccountSelectionHint, MessengerSetupShell, SetupInstructions } from "./IntegrationSetupUi";
import { CredentialInput } from "./CredentialInput";
import { channelConnectionState } from "../../channelConnectionState";
import { instagramOAuthCallbackType, type InstagramOAuthCallback } from "./metaCallbacks";

export function InstagramInlineSetup({
  businessId,
  canManage,
  channel,
}: {
  businessId: Id;
  canManage: boolean;
  channel?: BotChannel;
}) {
  const { t } = useI18n();
  const showNotification = useNotification();
  const queryClient = useQueryClient();
  const [instagramUserId, setInstagramUserId] = useState("");
  const [accessToken, setAccessToken] = useState("");
  const [pageId, setPageId] = useState("");
  const [username, setUsername] = useState("");
  const [oauthCode, setOauthCode] = useState("");
  const [oauthState, setOauthState] = useState("");
  const [oauthRedirectUri, setOauthRedirectUri] = useState("");
  const [showManualSetup, setShowManualSetup] = useState(false);
  const metaRedirectUri = `${window.location.origin}${window.location.pathname}?zani_provider=instagram`;

  function setNotice(message: string | null, tone: "success" | "info" | "warning" | "danger" = "info") {
    if (!message) return;
    showNotification({ message, tone });
  }

  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      if (event.origin !== window.location.origin || event.data?.type !== instagramOAuthCallbackType) return;
      const payload = event.data as InstagramOAuthCallback;
      if (payload.code) setOauthCode(payload.code);
      if (payload.state) setOauthState(payload.state);
      setNotice(t("integrations.instagram.metaAccessReturned"));
    };
    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, [t]);

  const status = useQuery({
    queryKey: ["instagram-status", channel?.id],
    queryFn: () => instagramChannelApi.status(Number(channel?.id)),
    enabled: Boolean(channel?.id),
  });

  const saveCredentials = useMutation({
    mutationFn: () => instagramChannelApi.configure({
      channelId: Number(channel?.id),
      providerMode: "meta_graph",
      instagramUserId,
      accessToken,
      pageId,
      username,
    }),
    onSuccess: () => {
      setInstagramUserId("");
      setAccessToken("");
      setPageId("");
      setUsername("");
      setNotice(t("integrations.instagram.accessSaved"));
      queryClient.invalidateQueries({ queryKey: ["bot-channels"] });
      queryClient.invalidateQueries({ queryKey: ["instagram-status", channel?.id] });
      queryClient.invalidateQueries({ queryKey: ["business-connectors"] });
    },
  });

	  const startOAuth = useMutation({
	    mutationFn: () => businessConnectorsApi.startInstagramOAuth({
	      business: businessId,
	      redirectUri: metaRedirectUri,
	      botChannel: channel?.id,
	    }),
    onSuccess: (data) => {
      setOauthState(data.state);
      setOauthRedirectUri(data.redirect_uri);
      if (!data.app_configured) {
        setNotice(t("integrations.instagram.metaOpenFailed"));
        return;
      }
      window.open(data.authorization_url, "zani_instagram_meta_oauth", "width=720,height=820");
    },
  });

	  const completeOAuth = useMutation({
	    mutationFn: () => businessConnectorsApi.completeInstagramOAuth({
	      business: businessId,
	      code: oauthCode,
	      state: oauthState,
	      redirect_uri: oauthRedirectUri || metaRedirectUri,
	      page_id: pageId,
    }),
    onSuccess: () => {
      setOauthCode("");
      setPageId("");
      setNotice(t("integrations.instagram.connectedNotice"));
      queryClient.invalidateQueries({ queryKey: ["bot-channels"] });
      queryClient.invalidateQueries({ queryKey: ["instagram-status", channel?.id] });
      queryClient.invalidateQueries({ queryKey: ["business-connectors"] });
    },
  });

  const testConnection = useMutation({
    mutationFn: () => instagramChannelApi.testConnection(Number(channel?.id)),
    onSuccess: (data) => {
      setNotice(data.ok ? t("integrations.instagram.connectionChecked") : merchantSafeIntegrationError(data.reason, t, canManage), data.ok ? "success" : "warning");
      queryClient.invalidateQueries({ queryKey: ["bot-channels"] });
      queryClient.invalidateQueries({ queryKey: ["instagram-status", channel?.id] });
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

  const error = saveCredentials.error || testConnection.error || startOAuth.error || completeOAuth.error || toggleChannel.error || status.error;
  const credentialsConfigured = Boolean(status.data?.instagram_user_id_configured && status.data?.access_token_configured);
  const hasOAuthResult = Boolean(oauthCode);
  const connection = channelConnectionState(channel);
  const busy = saveCredentials.isPending || testConnection.isPending || startOAuth.isPending || completeOAuth.isPending || toggleChannel.isPending;

  if (!channel) {
    return <ErrorState message={t("aiAgents.channelSetupUnavailable")} />;
  }

  return (
    <MessengerSetupShell
      logo="/integrations_logos/instagram.png"
      title="Instagram"
      description={t("integrations.setup.instagramDescription")}
      status={t(connection.key)}
      statusTone={connection.tone}
      loading={status.isPending}
      error={error ? <ErrorState message={merchantSafeIntegrationError(error, t, canManage)}
        action={status.isError ? <Button onClick={() => void status.refetch()}>{t("common.retry")}</Button> : undefined} /> : null}
      canManage={canManage && !busy && !status.isError}
      inboxChannel="instagram"
      channelToggleVisible={["active", "paused"].includes(channel.status)}
      channelEnabled={channel.status === "active"}
      channelToggleLoading={toggleChannel.isPending}
      onToggleChannel={(checked) => toggleChannel.mutate(checked ? "active" : "paused")}
      advancedOpen={showManualSetup}
      advancedLabel={t("integrations.setup.manualSetup")}
      onToggleAdvanced={() => setShowManualSetup((value) => !value)}
      instructions={!status.isError && !credentialsConfigured && !hasOAuthResult ? <SetupInstructions
        steps={[t("integrations.setup.externalStep1"), t("integrations.setup.instagramStep2"), t("integrations.setup.instagramStep3")]} /> : null}
      actions={!status.isError && !credentialsConfigured ? hasOAuthResult ? (
        <Button type="button" disabled={!canManage || busy || !oauthCode.trim() || !oauthState.trim()} isLoading={completeOAuth.isPending} onClick={() => completeOAuth.mutate()}>
          {t("integrations.instagram.completeConnection")}
        </Button>
      ) : <Button type="button" disabled={!canManage || busy} isLoading={startOAuth.isPending} onClick={() => startOAuth.mutate()}>
        {t("aiAgents.connect")}
      </Button> : null}
      advanced={
        <div className="space-y-3">
          <div className="grid gap-3 md:grid-cols-2">
            <Input label={t("integrations.instagram.accountId")} value={instagramUserId} onChange={(event) => setInstagramUserId(event.target.value)} placeholder={status.data?.instagram_user_id_configured ? t("integrations.instagram.idSaved") : "1784..."} />
            <CredentialInput label={t("integrations.card.accessKey")} value={accessToken} onChange={(event) => setAccessToken(event.target.value)} placeholder={status.data?.access_token_configured ? t("integrations.card.accessKeyReplacePlaceholder") : t("integrations.card.accessKeyPlaceholder")} disabled={!canManage || saveCredentials.isPending} />
            <Input label={t("integrations.instagram.facebookPageId")} value={pageId} onChange={(event) => setPageId(event.target.value)} placeholder={t("common.optional")} />
            <Input label={t("integrations.instagram.username")} value={username} onChange={(event) => setUsername(event.target.value)} placeholder="@account" />
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <Button type="button" disabled={!canManage || (!instagramUserId.trim() && !accessToken.trim())} isLoading={saveCredentials.isPending} onClick={() => saveCredentials.mutate()}>
              <ShieldCheck size={16} /> {credentialsConfigured ? t("integrations.instagram.updateAccess") : t("integrations.instagram.saveAccess")}
            </Button>
            <Button type="button" variant="secondary" disabled={!canManage || !credentialsConfigured} isLoading={testConnection.isPending} onClick={() => testConnection.mutate()}>
              <RefreshCw size={16} /> {t("integrations.card.check")}
            </Button>
          </div>
        </div>
      }
    >
      {!status.isError && !credentialsConfigured ? (
        <div className="space-y-4">
          {hasOAuthResult ? <p role="status" className="text-sm leading-6 text-platforma-subtle">{t("integrations.instagram.metaConfirmed")}</p> :
            <AccountSelectionHint kind="account" label={t("integrations.setup.instagramAccount")} hint={t("integrations.setup.professionalAccount")} />}
        </div>
      ) : null}
    </MessengerSetupShell>
  );
}

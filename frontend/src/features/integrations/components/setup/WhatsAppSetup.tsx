import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { botChannelsApi, whatsappChannelApi } from "../../../../api/bots";
import { Button } from "../../../../components/ui/Button";
import { ErrorState } from "../../../../components/ui/StateViews";
import { useNotification } from "../../../../components/notifications/NotificationProvider";
import { useI18n } from "../../../../lib/i18n";
import type { BotChannel, Id } from "../../../../types";
import { merchantSafeIntegrationError } from "../../utils";
import { AccountSelectionHint, MessengerSetupShell, SetupInstructions } from "./IntegrationSetupUi";
import { useWhatsAppSignup } from "./useWhatsAppSignup";
import { YCloudSetup } from "./YCloudSetup";
import { CredentialInput } from "./CredentialInput";
import { channelConnectionState } from "../../channelConnectionState";

export function WhatsAppInlineSetup({ businessId, canManage, channel }: {
  businessId: Id; canManage: boolean; channel?: BotChannel;
}) {
  const { t } = useI18n();
  const showNotification = useNotification();
  const queryClient = useQueryClient();
  const signup = useWhatsAppSignup(businessId, channel?.id,
    key => showNotification({ message: t(key), tone: "info" }));
  const status = useQuery({
    queryKey: ["whatsapp-status", channel?.id],
    queryFn: () => whatsappChannelApi.status(Number(channel?.id)),
    enabled: Boolean(channel?.id) && channel?.config_json?.provider_mode !== "ycloud",
  });
  const toggleChannel = useMutation({
    mutationFn: (nextStatus: BotChannel["status"]) => {
      if (!channel) throw new Error("Channel is required.");
      return botChannelsApi.update({ id: channel.id, payload: { status: nextStatus } });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["bot-channels"] });
      void queryClient.invalidateQueries({ queryKey: ["business-connectors"] });
    },
  });
  if (!channel) return <ErrorState message={t("aiAgents.channelSetupUnavailable")} />;
  if (channel.config_json?.provider_mode === "ycloud") return <YCloudSetup channel={channel} canManage={canManage} />;
  const connection = channelConnectionState(channel);
  const error = signup.start.error || signup.complete.error || toggleChannel.error || status.error;
  const busy = toggleChannel.isPending || signup.start.isPending || signup.waiting || signup.complete.isPending;
  const configured = Boolean(status.data?.phone_number_id_configured && status.data?.access_token_configured);
  return <MessengerSetupShell logo="/integrations_logos/whatsapp.png" title="WhatsApp" description={t("integrations.setup.whatsappDescription")}
    status={t(connection.key)} statusTone={connection.tone} loading={status.isPending}
    error={error ? <ErrorState message={merchantSafeIntegrationError(error, t, canManage)}
      action={status.isError ? <Button onClick={() => void status.refetch()}>{t("common.retry")}</Button> : undefined} /> : null}
    canManage={canManage && !busy && !status.isError} inboxChannel="whatsapp"
    channelToggleVisible={["active", "paused"].includes(channel.status)} channelEnabled={channel.status === "active"}
    channelToggleLoading={toggleChannel.isPending} onToggleChannel={checked => toggleChannel.mutate(checked ? "active" : "paused")}
    instructions={!status.isError && !configured && !signup.hasResult ? <SetupInstructions
      steps={[t("integrations.setup.externalStep1"), t("integrations.setup.whatsappStep2"), t("integrations.setup.whatsappStep3")]}
      note={t("integrations.setup.whatsappPinNote")} /> : null}
    actions={!status.isError && !configured ? <>
      {signup.waiting ? <Button type="button" variant="secondary" onClick={signup.cancel}>{t("common.cancel")}</Button> : null}
      <Button type="button" variant="primary" disabled={!canManage || busy || !signup.canStart} isLoading={signup.start.isPending || signup.complete.isPending}
        onClick={() => { signup.complete.reset(); signup.start.mutate(); }}>{t("aiAgents.connect")}</Button>
    </> : null}>
    {!status.isError && !configured ? <div className="space-y-4">
      <AccountSelectionHint kind="phone" label={t("integrations.setup.whatsappNumber")} hint={t("integrations.setup.whatsappLoginHint")} />
      <CredentialInput label={t("integrations.whatsapp.registrationPin")} inputMode="numeric" maxLength={6}
          value={signup.pin} onChange={event => signup.setPin(event.target.value.replace(/[^0-9]/g, ""))}
          disabled={!canManage || busy} />
      {signup.complete.isPending ? <p role="status" className="text-sm text-platforma-subtle">{t("integrations.whatsapp.metaDataReturned")}</p> : null}
    </div> : null}
  </MessengerSetupShell>;
}

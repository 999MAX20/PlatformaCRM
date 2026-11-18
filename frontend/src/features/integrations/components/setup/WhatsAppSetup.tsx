import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { botChannelsApi, whatsappChannelApi } from "../../../../api/bots";
import { Button } from "../../../../components/ui/Button";
import { Input } from "../../../../components/ui/Input";
import { Select } from "../../../../components/ui/Select";
import { ErrorState } from "../../../../components/ui/StateViews";
import { useNotification } from "../../../../components/notifications/NotificationProvider";
import { useI18n } from "../../../../lib/i18n";
import type { BotChannel, Id } from "../../../../types";
import { merchantSafeIntegrationError } from "../../utils";
import { AccountSelectionHint, MessengerSetupShell, SetupInstructions } from "./IntegrationSetupUi";
import { useWhatsAppSignup } from "./useWhatsAppSignup";
import { YCloudSetup } from "./YCloudSetup";
import { ycloudApi } from "../../../../api/ycloud";
import { CredentialInput } from "./CredentialInput";
import { channelConnectionState } from "../../channelConnectionState";

export function WhatsAppInlineSetup({ businessId, canManage, channel }: {
  businessId: Id; canManage: boolean; channel?: BotChannel;
}) {
  const { t } = useI18n();
  const showNotification = useNotification();
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [ycloudChannelId, setYcloudChannelId] = useState<Id | null>(null);
  const ycloud = useQuery({
    queryKey: ["ycloud-status", channel?.id],
    queryFn: () => ycloudApi.status(channel!.id),
    enabled: Boolean(channel?.id) && canManage && !channel?.external_id
      && !channel?.config_json?.connection_verified && !["active", "paused"].includes(channel?.status ?? ""),
  });
  const signup = useWhatsAppSignup(businessId, channel?.id,
    key => {
      if (key === "integrations.whatsapp.connectedNotice") setEditing(false);
      showNotification({ message: t(key), tone: "info" });
    });
  const status = useQuery({
    queryKey: ["whatsapp-status", channel?.id],
    queryFn: () => whatsappChannelApi.status(Number(channel?.id)),
    enabled: Boolean(channel?.id) && channel?.config_json?.provider_mode !== "ycloud",
    refetchInterval: query => query.state.data?.coexistence_sync && !["complete", "declined", "expired", "obsolete", "request_unknown"].includes(query.state.data.coexistence_sync.state) ? 5000 : false,
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
  if (channel.config_json?.provider_mode === "ycloud" || ycloudChannelId === channel.id) {
    return <YCloudSetup channel={channel} canManage={canManage} onBack={() => setYcloudChannelId(null)} />;
  }
  const connection = channelConnectionState(channel);
  const error = signup.start.error || signup.complete.error || toggleChannel.error || status.error;
  const busy = toggleChannel.isPending || signup.start.isPending || signup.waiting || signup.complete.isPending;
  const configured = Boolean(status.data?.phone_number_id_configured && status.data?.access_token_configured);
  const showSetup = !status.isError && (!configured || editing);
  const sync = status.data?.coexistence_sync;
  return <MessengerSetupShell logo="/integrations_logos/whatsapp.png" title="WhatsApp" description={t("integrations.setup.whatsappDescription")}
    status={t(connection.key)} statusTone={connection.tone} loading={status.isPending}
    error={error ? <ErrorState message={merchantSafeIntegrationError(error, t, canManage)}
      action={status.isError ? <Button onClick={() => void status.refetch()}>{t("common.retry")}</Button> : undefined} /> : null}
    canManage={canManage && !busy && !status.isError} inboxChannel="whatsapp"
    channelToggleVisible={["active", "paused"].includes(channel.status)} channelEnabled={channel.status === "active"}
    channelToggleLoading={toggleChannel.isPending} onToggleChannel={checked => toggleChannel.mutate(checked ? "active" : "paused")}
    instructions={showSetup && !signup.hasResult ? <SetupInstructions
      steps={[t("integrations.setup.externalStep1"), t("integrations.setup.whatsappStep2"), t("integrations.setup.whatsappStep3")]}
      note={t(signup.mode === "coexistence" ? "integrations.whatsapp.coexistenceNote" : "integrations.setup.whatsappPinNote")} /> : null}
    actions={showSetup ? <>
      {!configured && !editing && !channel.external_id && !channel.config_json?.connection_verified
        && !["active", "paused"].includes(channel.status) && ycloud.data?.available ?
        <Button type="button" variant="secondary" disabled={!canManage || busy}
          onClick={() => { signup.cancel(); setYcloudChannelId(channel.id); }}>{t("integrations.ycloud.connect")}</Button> : null}
      {editing && !busy ? <Button type="button" variant="secondary" onClick={() => { signup.cancel(); setEditing(false); }}>{t("common.cancel")}</Button> : null}
      {signup.waiting ? <Button type="button" variant="secondary" onClick={signup.cancel}>{t("common.cancel")}</Button> : null}
      <Button type="button" variant="primary" disabled={!canManage || busy || !signup.canStart} isLoading={signup.start.isPending || signup.complete.isPending}
        onClick={() => { signup.complete.reset(); signup.start.mutate(); }}>{t("aiAgents.connect")}</Button>
    </> : configured && canManage ? <Button type="button" variant="secondary" disabled={busy} onClick={() => setEditing(true)}>{t("integrations.whatsapp.changeConnection")}</Button> : null}>
    {sync && !editing ? <p role="status" className="text-sm text-platforma-subtle">
      {t(sync.state === "complete" ? "integrations.whatsapp.historyComplete" : sync.state === "declined" ? "integrations.whatsapp.historyDeclined"
        : ["expired", "obsolete", "request_unknown"].includes(sync.state) || sync.error_code ? "integrations.whatsapp.historyError" : "integrations.whatsapp.historyImporting")}
    </p> : null}
    {showSetup ? <div className="space-y-4">
      <Select label={t("integrations.ycloud.mode")} value={signup.mode} disabled={!canManage || busy}
        options={[{ value: "cloud", label: t("integrations.ycloud.apiMode") }, { value: "coexistence", label: t("integrations.ycloud.appMode") }]}
        onChange={event => signup.setMode(event.target.value === "coexistence" ? "coexistence" : "cloud")} />
      {signup.mode === "cloud" ? <AccountSelectionHint kind="phone" label={t("integrations.setup.whatsappNumber")} hint={t("integrations.setup.whatsappLoginHint")} /> : null}
      {signup.mode === "coexistence" ? <Input type="tel" autoComplete="tel" label={t("integrations.whatsapp.businessAppNumber")}
        placeholder="+7…" value={signup.phone} disabled={!canManage || busy}
        onChange={event => signup.setPhone(event.target.value.replace(/[ ()-]/g, ""))} /> : <CredentialInput label={t("integrations.whatsapp.registrationPin")} inputMode="numeric" maxLength={6}
          value={signup.pin} onChange={event => signup.setPin(event.target.value.replace(/[^0-9]/g, ""))}
          disabled={!canManage || busy} />}
      {signup.complete.isPending ? <p role="status" className="text-sm text-platforma-subtle">{t("integrations.whatsapp.metaDataReturned")}</p> : null}
    </div> : null}
  </MessengerSetupShell>;
}

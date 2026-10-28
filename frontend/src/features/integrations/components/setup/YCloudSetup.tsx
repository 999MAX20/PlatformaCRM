import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ExternalLink, RefreshCw } from "lucide-react";

import { ycloudApi } from "../../../../api/ycloud";
import { botChannelsApi } from "../../../../api/bots";
import { Button } from "../../../../components/ui/Button";
import { ErrorState, LoadingState } from "../../../../components/ui/StateViews";
import { useI18n } from "../../../../lib/i18n";
import type { BotChannel } from "../../../../types";
import { MessengerSetupShell } from "./IntegrationSetupUi";

export function YCloudSetup({ channel, canManage, onBack }: { channel: BotChannel; canManage: boolean; onBack?: () => void }) {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [signupLink, setSignupLink] = useState<{ url: string; expiresAt: number } | null>(null);
  const status = useQuery({ queryKey: ["ycloud-status", channel.id], queryFn: () => ycloudApi.status(channel.id), refetchInterval: 5000 });
  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["ycloud-status", channel.id] });
    void queryClient.invalidateQueries({ queryKey: ["bot-channels"] });
    void queryClient.invalidateQueries({ queryKey: ["business-connectors"] });
  };
  const start = useMutation({ mutationFn: () => ycloudApi.start(channel.id), onSuccess: (data) => {
    // Memory only. Do not persist the temporary credential in query/local storage.
    const url = new URL(data.onboarding_url);
    if (url.origin === "https://connect.ycloud.com" && url.pathname === "/open/whatsapp/onboard") {
      setSignupLink({ url: data.onboarding_url, expiresAt: Date.parse(data.expires_at) });
    }
    invalidate();
  } });
  const recover = useMutation({ mutationFn: (action: "cancel" | "retry_events") => ycloudApi.recover(channel.id, action), onSuccess: () => { setSignupLink(null); invalidate(); } });
  const toggle = useMutation({ mutationFn: (enabled: boolean) => botChannelsApi.update({ id: channel.id, payload: { status: enabled ? "active" : "paused" } }), onSuccess: invalidate });
  const data = status.data;
  const pending = data?.status === "pending";
  const connected = data?.status === "connected";
  const paused = data?.channel_status === "paused";
  const busy = start.isPending || recover.isPending || toggle.isPending;
  const refresh = () => {
    start.reset();
    recover.reset();
    toggle.reset();
    void status.refetch();
  };
  const error = status.error || start.error || recover.error || toggle.error;
  const statusLabel = !data ? t("common.loading") : !data.available ? t("integrations.ycloud.setupRequired")
    : connected ? t(paused ? "integrations.status.paused" : "integrations.status.connected")
    : pending ? t("integrations.ycloud.pending") : data.status === "expired" ? t("integrations.ycloud.expired") : t("integrations.status.notConnected");
  return <MessengerSetupShell title="WhatsApp" logo="/integrations_logos/whatsapp.png"
    description={t("integrations.ycloud.connection")} status={statusLabel} canManage={canManage} inboxChannel="whatsapp"
    statusTone={connected && !paused ? "success" : pending ? "progress" : "neutral"}
    channelToggleVisible={connected} channelEnabled={!paused && data?.channel_status === "active"}
    channelToggleLoading={toggle.isPending} onToggleChannel={(value) => toggle.mutate(value)}
    error={error ? <ErrorState message={t("integrations.ycloud.requestFailed")} action={<Button onClick={refresh}>{t("common.retry")}</Button>} /> : null}>
    {status.isPending ? <LoadingState /> : <div className="space-y-3" data-testid="ycloud-setup">
      {data?.phone_number ? <p className="font-semibold text-platforma-text">{data.phone_number}</p> : null}
      {!data?.available ? <p role="status" className="text-sm text-platforma-muted">{t("integrations.ycloud.setupRequired")}</p> : null}
      {pending ? <p role="status" className="text-sm text-platforma-muted">{t("integrations.ycloud.pending")}</p> : null}
      {data?.error_code || data?.failed_events ? <p role="alert" className="text-sm text-platforma-danger">{t("integrations.ycloud.needsAttention")}</p> : null}
      <div className="flex flex-wrap gap-3">
        {!connected && !pending ? <Button disabled={!canManage || !data?.available || busy} isLoading={start.isPending} onClick={() => start.mutate()}>{t("integrations.ycloud.connect")}</Button> : null}
        {pending && signupLink && signupLink.expiresAt > Date.now() ? <a className="inline-flex min-h-11 items-center gap-2 rounded-control px-3 font-bold text-brand-700 focus-visible:outline focus-visible:outline-2" href={signupLink.url} target="_blank" rel="noopener noreferrer" referrerPolicy="no-referrer"><ExternalLink size={16} />{t("integrations.ycloud.openSignup")}</a> : null}
        {pending ? <Button variant="secondary" disabled={!canManage || busy} onClick={() => recover.mutate("cancel")}>{t("common.cancel")}</Button> : null}
        {Boolean(data?.error_code || data?.failed_events) ? <Button variant="secondary" disabled={!canManage || busy || !data?.available} onClick={() => recover.mutate("retry_events")}>{t("common.retry")}</Button> : null}
        <Button variant="ghost" isLoading={status.isFetching} onClick={refresh}><RefreshCw size={16} />{t("common.refresh")}</Button>
        {onBack && !pending && !connected ? <Button variant="ghost" onClick={onBack}>{t("integrations.ycloud.otherMethod")}</Button> : null}
      </div>
    </div>}
  </MessengerSetupShell>;
}

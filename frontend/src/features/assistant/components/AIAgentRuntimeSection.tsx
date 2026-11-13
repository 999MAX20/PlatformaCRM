import { ArrowUpRight } from "lucide-react";
import { cn } from "../../../lib/cn";
import { LogoMark } from "../../integrations/components/setup/IntegrationSetupUi";
import { providerCatalog } from "../../integrations/config/providerCatalog";
import { Link } from "react-router";
import { useI18n } from "../../../lib/i18n";
import type { Bot, BotChannel } from "../../../types";
import type { OnboardingStep } from "../aiAgentsTypes";
import { OnboardingProgress } from "./AIAgentsShared";
import { AIAgentPreview } from "./AIAgentPreview";
import { CustomerAgentActivity } from "./CustomerAgentActivity";
import { channelStatus, channelStatusClass } from "../aiAgentsUtils";

export function TestAndLaunchSection({ bot, dirty, canTest, fillHeight = false }: {
  bot: Bot; dirty: boolean; canTest: boolean; fillHeight?: boolean;
}) {
  return <AIAgentPreview key={`${bot.id}-${bot.updated_at}`} botId={bot.id} blocked={dirty || !bot.readiness?.profile_ready} canTest={canTest} fillHeight={fillHeight} />;
}

export function CustomerAgentOverview({ bot, onboardingSteps, channels, canViewChannels, canManageChannels }: {
  bot: Bot; onboardingSteps: OnboardingStep[]; channels: BotChannel[]; canViewChannels: boolean; canManageChannels: boolean;
}) {
  const { t } = useI18n();
  return <div className="mx-auto w-full max-w-[880px] space-y-6" data-testid="agent-overview">
    <OnboardingProgress steps={onboardingSteps} />
    <CustomerAgentActivity bot={bot} />
    {canViewChannels && <section className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-base font-semibold">{t("aiAgents.channelsTitle")}</h3>
        <Link className="platforma-focus-ring inline-flex min-h-11 items-center text-sm font-semibold text-brand-800 underline" to={`/app/ai-agents/${bot.id}/channels`}>{t("aiAgents.configure")}</Link>
      </div>
      {channels.length ? <div className="grid max-w-[732px] gap-3 sm:grid-cols-2">{channels.map(channel => {
        const title = t(`channel.${channel.channel}`);
        const actionKey = channel.status === "draft" ? "aiAgents.channel.finishSetup" : channel.status === "error" ? "aiAgents.channel.checkConnection" : "aiAgents.channel.openSettings";
        return <article key={channel.id} className="w-full min-w-0 max-w-[360px] rounded-xl border border-platforma-border bg-white p-4">
          <div className="flex flex-wrap items-start gap-3">
            <LogoMark compact logo={providerCatalog.find(provider => provider.provider === channel.channel)?.logo} label={title} />
            <div className="min-w-0">
              <h4 className="break-words text-sm font-semibold text-platforma-ink">{title}</h4>
              <span className={cn("mt-2 inline-block max-w-full break-words rounded-md px-2 py-1 text-xs font-semibold ring-1", channelStatusClass(channel))}>{channelStatus(channel, t)}</span>
            </div>
          </div>
          <Link className="platforma-focus-ring mt-3 inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-brand-800 underline sm:min-h-9"
            to={`/app/ai-agents/${bot.id}/channels${canManageChannels ? `?channel=${channel.channel}` : ""}`}>
            {t(canManageChannels ? actionKey : "aiAgents.channel.openSettings")}<ArrowUpRight aria-hidden="true" size={16} className="shrink-0" />
          </Link>
        </article>;
      })}</div> : <p className="text-sm text-platforma-subtle">{t("aiAgents.status.notConnected")}</p>}
    </section>}
  </div>;
}

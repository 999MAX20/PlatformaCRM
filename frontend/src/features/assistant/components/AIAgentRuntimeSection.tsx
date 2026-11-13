import { Link } from "react-router";
import { useI18n } from "../../../lib/i18n";
import type { Bot, BotChannel } from "../../../types";
import type { OnboardingStep } from "../aiAgentsTypes";
import { OnboardingProgress } from "./AIAgentsShared";
import { AIAgentPreview } from "./AIAgentPreview";
import { CustomerAgentActivity } from "./CustomerAgentActivity";
import { channelStatus } from "../aiAgentsUtils";

export function TestAndLaunchSection({ bot, dirty, canTest }: {
  bot: Bot; dirty: boolean; canTest: boolean;
}) {
  return <AIAgentPreview key={`${bot.id}-${bot.updated_at}`} botId={bot.id} blocked={dirty || !bot.readiness?.profile_ready} canTest={canTest} />;
}

export function CustomerAgentOverview({ bot, onboardingSteps, channels, canViewChannels }: {
  bot: Bot; onboardingSteps: OnboardingStep[]; channels: BotChannel[]; canViewChannels: boolean;
}) {
  const { t } = useI18n();
  return <div className="space-y-6">
    {!bot.readiness?.configured_ready && <OnboardingProgress compact steps={onboardingSteps} />}
    <CustomerAgentActivity bot={bot} />
    {canViewChannels && <section className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-base font-semibold">{t("aiAgents.channelsTitle")}</h3>
        <Link className="platforma-focus-ring inline-flex min-h-11 items-center text-sm font-semibold text-brand-800 underline" to={`/app/ai-agents/${bot.id}/channels`}>{t("aiAgents.configure")}</Link>
      </div>
      {channels.length ? <dl className="divide-y divide-platforma-border">{channels.map(channel => <div key={channel.id} className="flex flex-wrap justify-between gap-3 py-3 text-sm">
        <dt>{t(`channel.${channel.channel}`)}</dt><dd className="text-platforma-subtle">{channelStatus(channel, t)}</dd>
      </div>)}</dl> : <p className="text-sm text-platforma-subtle">{t("aiAgents.status.notConnected")}</p>}
    </section>}
  </div>;
}

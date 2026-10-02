import { statusNoticeTones } from "../../../components/ui/StatusNotice";
import { useI18n } from "../../../lib/i18n";
import type { Bot } from "../../../types";
import type { OnboardingStep } from "../aiAgentsTypes";
import { OnboardingProgress } from "./AIAgentsShared";
import { AIAgentPreview } from "./AIAgentPreview";

export function TestAndLaunchSection({ bot, onboardingSteps, launchReady, dirty, canTest }: {
  bot: Bot; onboardingSteps: OnboardingStep[]; launchReady: boolean; dirty: boolean; canTest: boolean;
}) {
  const { t } = useI18n();
  const notice = statusNoticeTones[launchReady ? "success" : "warning"];
  const NoticeIcon = notice.Icon;
  return <div className="flex flex-col gap-3">
    <details className={`rounded-control border px-3 py-2 text-sm ${notice.container}`}>
      <summary className="platforma-focus-ring min-h-7 cursor-pointer py-1 font-semibold">
        <NoticeIcon aria-hidden="true" size={18} className={`mr-2 inline-block align-text-bottom ${notice.icon}`} />
        {t(launchReady ? "aiAgents.hint.launchReady" : "aiAgents.activationBlocked")}
      </summary>
      <p className="mt-2 leading-5 text-platforma-subtle">{t("aiSetup.launchHelp")}</p>
    </details>
    <OnboardingProgress compact steps={onboardingSteps} />
    <AIAgentPreview key={`${bot.id}-${bot.updated_at}`} botId={bot.id} blocked={dirty || !bot.readiness?.profile_ready} canTest={canTest} />
  </div>;
}

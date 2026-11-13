import { Link } from "react-router";
import { Button } from "../../../components/ui/Button";
import { useI18n } from "../../../lib/i18n";
import type { Bot } from "../../../types";

export function AgentReadiness({ bot, dirty, onRefresh }: { bot: Bot; dirty: boolean; onRefresh: () => void }) {
  const { t } = useI18n();
  const readiness = bot.readiness;
  if (!readiness?.provider) return null;
  const provider = readiness.provider;
  const warning = !readiness.is_ready || Boolean(readiness.booking?.missing.length);
  const firstMissing = readiness.missing[0];
  const reason = firstMissing ? t(`aiAgents.readiness.missing.${firstMissing}`)
    : !provider.configuration_ready ? t(`aiAgents.readiness.provider.${provider.state}`)
    : readiness.booking?.missing[0] ? t(`aiAgents.readiness.booking.${readiness.booking.missing[0]}`) : null;
  return <details className="text-sm" data-testid="agent-readiness">
    <summary className="platforma-focus-ring min-h-11 cursor-pointer py-3 font-semibold text-platforma-ink">
      {t(warning ? "aiAgents.readiness.needsAttention" : "aiAgents.readiness.configurationComplete")}
      {reason && <span className="mt-1 block font-normal text-platforma-subtle">{reason}</span>}
    </summary>
    <div className="space-y-2 pb-3 text-platforma-subtle">
      {dirty && <p>{t("aiAgents.readiness.savedConfiguration")}</p>}
      <p>{t(`aiAgents.readiness.provider.${provider.state}`)}</p>
      {provider.model && <p className="break-words">{t("aiAgents.readiness.effectiveModel", { model: provider.model })}</p>}
      <p>{t("aiAgents.readiness.runtimeChecks")}</p>
      {readiness.missing.map(item => <p key={item}><Link className="platforma-focus-ring underline" to={`/app/ai-agents/${bot.id}/${item === "channel" ? "channels" : item}`}>
        {t(`aiAgents.readiness.missing.${item}`)}
      </Link></p>)}
      {readiness.booking?.missing.map(item => <p key={item}>{t(`aiAgents.readiness.booking.${item}`)}</p>)}
      <Button type="button" size="sm" variant="secondary" onClick={onRefresh}>{t("common.refresh")}</Button>
    </div>
  </details>;
}

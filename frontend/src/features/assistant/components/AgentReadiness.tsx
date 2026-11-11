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
  return <details className="mt-3 text-sm" data-testid="agent-readiness" open={warning ? true : undefined}>
    <summary className="platforma-focus-ring min-h-11 cursor-pointer py-3 font-semibold text-platforma-ink">
      {t(warning ? "aiAgents.readiness.needsAttention" : "aiAgents.readiness.configurationComplete")}
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

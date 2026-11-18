import type { AgentPreviewResponse } from "../../../api/bots";
import { useI18n } from "../../../lib/i18n";

export function AgentPreviewExplanation({ result }: { result: AgentPreviewResponse }) {
  const { t } = useI18n();
  const decision = result.handoff_required ? "handoff" : result.reply ? "reply" : "noReply";
  const reason = ({ safety_handoff: "safety", blocked_low_confidence: "confidence", blocked_fallback: "fallback",
    blocked_risky_intent: "review", needs_review: "review" } as Record<string, string>)[result.decision];
  return (
    <details className="mt-2 min-w-0 text-xs text-platforma-subtle">
      <summary className="platforma-focus-ring cursor-pointer rounded-control py-2 font-semibold">
        {t("aiSetup.explanation")}
      </summary>
      <div className="grid min-w-0 gap-2 pb-1 break-words">
        <p>{t(`aiSetup.result.${decision}`)}</p>
        {reason && <p>{t(`aiSetup.result.reason.${reason}`)}</p>}
        {result.summary && <p className="whitespace-pre-wrap">{result.summary}</p>}
        <div>
          <p className="font-semibold">{t("aiSetup.result.sources")}</p>
          {result.sources.length ? <ul className="list-disc space-y-1 pl-4">
            {result.sources.map((source, index) => <li key={`${source.type}:${source.id}:${index}`}>{source.label}</li>)}
          </ul> : <p>{t("aiSetup.result.noSources")}</p>}
        </div>
        <p>{t(`aiSetup.result.provider.${result.provider_state}`)}{result.provider_state !== "not_called" && result.model ? ` · ${result.model}` : ""}</p>
        <p>{t(result.automatic_reply_enabled && !result.handoff_required ? "aiSetup.result.autoAllowed" : "aiSetup.result.autoBlocked")}</p>
        <p>{t("aiSetup.result.simulation")}</p>
      </div>
    </details>
  );
}

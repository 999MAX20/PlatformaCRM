import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { botAiApi, type AgentPreviewMessage } from "../../../api/bots";
import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { Textarea } from "../../../components/ui/Textarea";
import { StatusNotice } from "../../../components/ui/StatusNotice";
import { ErrorState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";

export function AIAgentPreview({ botId, blocked, canTest, fillHeight = false }: { botId: number; blocked: boolean; canTest: boolean; fillHeight?: boolean }) {
  const { t } = useI18n();
  const [text, setText] = useState("");
  const [messages, setMessages] = useState<AgentPreviewMessage[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const preview = useMutation({
    mutationFn: (history: AgentPreviewMessage[]) => botAiApi.preview(botId, history),
    onSuccess: (result, history) => {
      setMessages([...history, ...(result.reply ? [{ direction: "outbound" as const, text: result.reply }] : [])]);
      setText("");
    },
  });
  const disabled = blocked || !canTest || preview.isPending;
  useEffect(() => {
    if (fillHeight && scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [fillHeight, messages, preview.error]);
  return (
    <section className={`flex flex-col gap-3 ${fillHeight ? "min-h-0 flex-1 overflow-y-auto overscroll-contain" : ""}`}>
      <div ref={scrollRef} className={`space-y-3 ${fillHeight ? "min-h-32 flex-1 overflow-y-auto overscroll-contain" : ""}`}>
        <p className="text-sm font-semibold text-platforma-ink">{t("aiAgents.previewSavedConfiguration")}</p>
        <p className="text-sm text-platforma-subtle">{t("aiSetup.previewScope")}</p>
        {!canTest ? <ErrorState message={t("aiSetup.previewForbidden")} /> : blocked ? (
          <StatusNotice compact tone="warning" title={t("aiSetup.saveBeforeTest")} />
        ) : null}
        <div className="flex flex-wrap gap-2">
          {["price", "booking", "complaint"].map((scenario) => (
            <Button key={scenario} type="button" size="sm" className="min-h-11 sm:min-h-9" variant="secondary" disabled={disabled} onClick={() => setText(t(`aiSetup.example.${scenario}`))}>
              {t(`aiSetup.scenario.${scenario}`)}
            </Button>
          ))}
        </div>
        <div role="log" aria-label={t("aiSetup.previewTitle")} className={`${fillHeight ? "" : "max-h-80 overflow-y-auto overscroll-contain"} space-y-3 rounded-control bg-surface-muted ${messages.length ? "min-h-32 p-3" : "h-0"}`}>
          {messages.map((message, index) => (
            <div key={index} className="border-b border-platforma-border pb-2 last:border-0 last:pb-0">
              <p className="text-xs font-semibold text-platforma-subtle">{t(message.direction === "inbound" ? "aiAgents.client" : "aiAgents.reply")}</p>
              <p className="whitespace-pre-wrap break-words text-sm">{message.text}</p>
            </div>
          ))}
        </div>
        {preview.data ? <div className="space-y-2" aria-live="polite">
          <StatusNotice compact tone={preview.data.handoff_required ? "warning" : "success"}
            title={t(preview.data.handoff_required ? "aiSetup.handoff" : preview.data.automatic_reply_enabled ? "aiSetup.automatic" : "aiSetup.draftOnly")}
            description={preview.data.summary} />
          <p className="text-sm text-platforma-subtle">{t(preview.data.provider_state === "not_called" ? "customerSafety.noProviderCall" : preview.data.provider_state === "live" ? "aiAgents.aiProviderLive" : "aiQuality.mock")}</p>
          {preview.data.sources.length ? <ul aria-label={t("aiAgents.aiSources")} className="flex flex-wrap gap-2 text-xs text-platforma-subtle">
            {preview.data.sources.map((source) => <li key={`${source.type}-${source.id}`}>{source.label}</li>)}
          </ul> : null}
        </div> : null}
        {preview.error ? <ErrorState error={preview.error} message={getApiErrorMessage(preview.error)} /> : null}
      </div>
        <form className={`grid shrink-0 gap-3 ${fillHeight ? "border-t border-platforma-border pt-3" : ""}`} onSubmit={(event) => {
          event.preventDefault();
          if (!disabled && text.trim()) preview.mutate([...messages.slice(-14), { direction: "inbound", text: text.trim() }]);
        }}>
          <Textarea className="min-h-20 py-2" rows={2} label={t("aiSetup.message")} value={text} maxLength={2000} disabled={disabled} onChange={(event) => setText(event.target.value)} />
          <div className="flex flex-wrap gap-2">
            <Button type="submit" className="min-h-11" disabled={disabled || !text.trim()} isLoading={preview.isPending}>{t("aiSetup.testReply")}</Button>
            <Button type="button" className="min-h-11 sm:min-h-10" variant="secondary" disabled={preview.isPending} onClick={() => { setMessages([]); setText(""); preview.reset(); }}>{t("aiSetup.resetTest")}</Button>
          </div>
        </form>
    </section>
  );
}

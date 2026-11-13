import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { LoaderCircle, RotateCcw, SendHorizontal } from "lucide-react";
import { botAiApi, type AgentPreviewMessage } from "../../../api/bots";
import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { Textarea } from "../../../components/ui/Textarea";
import { useI18n } from "../../../lib/i18n";

export function AIAgentPreview({ botId, blocked, canTest, fillHeight = false }: { botId: number; blocked: boolean; canTest: boolean; fillHeight?: boolean }) {
  const { t } = useI18n();
  const [text, setText] = useState("");
  const [messages, setMessages] = useState<AgentPreviewMessage[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const preview = useMutation({
    mutationFn: (history: AgentPreviewMessage[]) => botAiApi.preview(botId, history),
    onSuccess: (result, history) => {
      setMessages([...history, ...(result.reply ? [{ direction: "outbound" as const, text: result.reply }] : [])]);
      setText("");
    },
  });
  const disabled = blocked || !canTest || preview.isPending;
  const unavailable = !canTest ? t("aiSetup.previewForbidden") : blocked ? t("aiSetup.saveBeforeTest") : "";
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);
  return (
    <section className={`flex flex-col gap-3 ${fillHeight ? "min-h-0 flex-1 overflow-y-auto overscroll-contain" : ""}`}>
      <div ref={scrollRef} role="log" aria-label={t("aiSetup.previewTitle")}
        className={`space-y-3 overflow-y-auto overscroll-contain ${fillHeight ? "min-h-0 flex-1" : "max-h-80"}`}>
        {messages.map((message, index) => (
          <div key={index} className="border-b border-platforma-border pb-2 last:border-0">
            <p className="text-xs font-semibold text-platforma-subtle">{t(message.direction === "inbound" ? "aiAgents.client" : "aiAgents.reply")}</p>
            <p className="whitespace-pre-wrap break-words text-sm">{message.text}</p>
          </div>
        ))}
        {preview.data && !preview.data.reply && preview.data.summary && <p className="whitespace-pre-wrap break-words text-sm text-platforma-subtle">{preview.data.summary}</p>}
      </div>
      <form className="grid min-w-0 w-full shrink-0 gap-2" onSubmit={event => {
        event.preventDefault();
        if (!disabled && text.trim()) preview.mutate([...messages.slice(-14), { direction: "inbound", text: text.trim() }]);
      }}>
        {!messages.length && <div className="grid gap-1">
          {["price", "booking", "complaint"].map(scenario => (
            <button key={scenario} type="button" disabled={disabled}
              className="platforma-focus-ring min-h-7 rounded-control px-2 py-1 text-left text-xs leading-4 text-platforma-subtle hover:bg-surface-hover active:bg-surface-muted disabled:cursor-not-allowed disabled:text-disabled-content"
              onClick={() => { setText(t(`aiSetup.example.${scenario}`)); inputRef.current?.focus(); }}>
              {t(`aiSetup.example.${scenario}`)}
            </button>
          ))}
        </div>}
        {unavailable && <p className="text-xs text-platforma-subtle" role="status">{unavailable}</p>}
        {preview.error && <p className="text-xs text-platforma-danger" role="alert">{getApiErrorMessage(preview.error)}</p>}
        <div className="flex min-w-0 items-end gap-2">
          <div className="min-w-0 flex-1">
            <Textarea ref={inputRef} className="block !min-h-11 max-h-40 py-2" rows={1} label={t("aiAgents.previewMessage")}
              value={text} maxLength={2000} disabled={disabled} onChange={event => setText(event.target.value)} />
          </div>
          <Button type="submit" className="h-[44px] min-h-[44px] w-[44px] shrink-0 p-0" disabled={disabled || !text.trim()} aria-busy={preview.isPending || undefined}
            aria-label={t("aiSetup.testReply")} title={t("aiSetup.testReply")}>
            {preview.isPending ? <LoaderCircle size={18} className="animate-spin motion-reduce:animate-none" aria-hidden="true" /> : <SendHorizontal size={18} aria-hidden="true" />}
          </Button>
          {messages.length > 0 && <Button type="button" className="h-[44px] min-h-[44px] w-[44px] shrink-0 p-0" variant="secondary" disabled={preview.isPending}
            aria-label={t("aiSetup.resetTest")} title={t("aiSetup.resetTest")}
            onClick={() => { setMessages([]); setText(""); preview.reset(); inputRef.current?.focus(); }}><RotateCcw size={16} aria-hidden="true" /></Button>}
        </div>
      </form>
    </section>
  );
}

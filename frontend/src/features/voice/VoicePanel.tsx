import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router";
import { Mic, ArrowUp, RotateCcw, LoaderCircle } from "lucide-react";
import { speechApi, type SpeechStatus } from "../../api/speech";
import { Button } from "../../components/ui/Button";
import { Textarea } from "../../components/ui/Textarea";
import { ErrorState, InlineFallback, LoadingState } from "../../components/ui/StateViews";
import { useRecoveryDelay } from "../../components/actions/useRecoveryDelay";
import { useI18n } from "../../lib/i18n";
import { hasPermission } from "../../lib/permissions";
import { useAuth } from "../auth/AuthProvider";
import { VoiceWaveform } from "./VoiceWaveform";
import { VoiceTurnResult } from "./VoiceTurnResult";
import { useVoiceRecorder } from "./useVoiceRecorder";
import { useVoicePreferences } from "./useVoicePreferences";
import { useVoiceConversation } from "./useVoiceConversation";
import type { Id } from "../../types";
import { voiceCardContext } from "./context";
import { speechFailure } from "./speechFailure";

export function VoicePanel({ userId, status, currentEntity, currentBranch, initialConversation }: { userId: Id; status: SpeechStatus; currentEntity?: ReturnType<typeof voiceCardContext>; currentBranch?: number; initialConversation?: string }) {
  const { t } = useI18n(); const { user } = useAuth();
  const { preferences } = useVoicePreferences(userId);
  const recorder = useVoiceRecorder();
  const chat = useVoiceConversation(userId, status.business, initialConversation);
  const [draft, setDraft] = useState(false);
  const [recorded, setRecorded] = useState<Blob | null>(null);
  const [unsent, setUnsent] = useState<string | null>(null);
  const [text, setText] = useState(""); const [transcribing, setTranscribing] = useState(false);
  const [error, setError] = useState<unknown>(null); const [includeContext, setIncludeContext] = useState(false);
  const [speechError, setSpeechError] = useState<unknown>(null);
  const speechIssue = useMemo(() => speechFailure(speechError), [speechError]);
  const speechRetryDelay = useRecoveryDelay(speechIssue.error);
  const abort = useRef<AbortController | null>(null); const textInput = useRef<HTMLTextAreaElement>(null);
  const focusTranscript = useRef(false);
  useEffect(() => () => { abort.current?.abort(); }, []);
  useEffect(() => { if (!transcribing && focusTranscript.current) { focusTranscript.current = false; textInput.current?.focus(); } }, [transcribing]);
  function cancelAudio() { recorder.cancel(); abort.current?.abort(); abort.current = null; setTranscribing(false); setRecorded(null); setSpeechError(null); }
  async function submit(message: string) {
    setUnsent(message);
    await chat.send.mutateAsync({ message, currentEntity: includeContext ? currentEntity : undefined, currentBranch });
    setUnsent(null); setText(""); setDraft(false);
  }
  async function stop(send = true) {
    const controller = new AbortController(); abort.current = controller;
    setTranscribing(send); setError(null); setSpeechError(null);
    let recognizing = true;
    try {
      const audio = recorded || await recorder.stop();
      if (!audio || controller.signal.aborted) return;
      setRecorded(audio);
      if (!send) return;
      const result = await speechApi.transcribe(status.business, audio, preferences.language, controller.signal,
        includeContext ? currentEntity : undefined);
      if (controller.signal.aborted) return;
      recognizing = false;
      setRecorded(null); setTranscribing(false); abort.current = null;
      await submit(result.text);
    } catch (cause) { if (!controller.signal.aborted) { if (recognizing) setSpeechError(cause); else setError(cause); } }
    finally { if (abort.current === controller && !controller.signal.aborted) setTranscribing(false); }
  }
  recorder.limitCallback.current = () => { void stop(false); };
  const audioBusy = recorder.state !== "idle" || transcribing;
  const canExecute = hasPermission(user, status.business, "ai_pipeline", "approve") && hasPermission(user, status.business, "ai_pipeline", "execute");
  const showResult = !audioBusy && !recorded && !draft && !chat.send.isPending && chat.latest && !chat.history.isError;
  return <div className="space-y-4" data-testid="voice-panel-content">
    {chat.history.isLoading && <LoadingState />}
    {chat.history.error && <ErrorState error={chat.history.error} action={<Button onClick={() => chat.history.refetch()}>{t("common.retry")}</Button>} />}
    {chat.send.isPending && <p role="status" className="text-sm text-platforma-subtle">{t("agentChat.status.preparing")}</p>}
    {showResult && <VoiceTurnResult turn={chat.latest!} busy={chat.action.isPending} canExecute={canExecute}
      onAction={kind => chat.action.mutate({ kind, turn: chat.latest! })} />}
    {showResult && ["awaiting_confirmation", "clarifying"].includes(chat.latest!.status) && <Button variant="secondary" disabled={chat.busy}
      onClick={() => { setText(chat.latest!.message); setDraft(true); focusTranscript.current = true; requestAnimationFrame(() => textInput.current?.focus()); }}>{t("voice.editRequest")}</Button>}
    {speechError != null && <InlineFallback error={speechIssue.error}
      title={speechIssue.messageKey ? t("voice.speechError.title") : undefined}
      message={speechIssue.messageKey ? t(speechIssue.messageKey) : undefined} />}
    {(error || chat.send.error || chat.action.error) && <ErrorState error={error || chat.send.error || chat.action.error} />}
    {recorder.error && <p role="alert" className="text-sm text-platforma-danger">{t(`voice.error.${recorder.error}`)}</p>}
    {!status.ready && <p role="status" className="text-sm text-platforma-subtle">{t("voice.unavailable")}</p>}
    {unsent && !chat.busy && <Button onClick={() => { setError(null); void submit(unsent).catch(setError); }}>{t("common.retry")}</Button>}
    {currentEntity && !audioBusy && <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={includeContext} disabled={chat.busy || Boolean(unsent)}
      onChange={event => setIncludeContext(event.target.checked)} />{t("voice.context", { entity: t(`aiWorkflow.source.${currentEntity.entity}`), id: currentEntity.id })}</label>}
    {draft && !audioBusy && <form className="space-y-3" onSubmit={event => {
      event.preventDefault();
      if (!text.trim() || chat.busy || chat.history.isError) return;
      setError(null);
      chat.send.mutate({ message: text.trim(), currentEntity: includeContext ? currentEntity : undefined, currentBranch }, {
        onSuccess: () => { setText(""); setDraft(false); },
      });
    }}>
      <Textarea ref={textInput} label={t("voice.transcript")} value={text} maxLength={4000} disabled={chat.busy} onChange={event => setText(event.target.value)} />
      <div className="flex justify-end"><Button type="submit" size="icon" aria-label={t("agentChat.send")} disabled={!text.trim() || chat.busy || chat.history.isError}
        aria-busy={chat.send.isPending}>{chat.send.isPending ? <LoaderCircle size={20} className="motion-safe:animate-spin" aria-hidden="true" /> : <ArrowUp size={20} aria-hidden="true" />}</Button></div>
    </form>}
    <div className={audioBusy || recorded ? "space-y-3" : "flex min-h-20 items-center gap-3"}>
      {audioBusy || recorded ? <>
        {recorder.state === "recording" ? <VoiceWaveform values={recorder.waveform} level={recorder.level} seconds={recorder.seconds} />
          : <p role="status" className="py-4 text-center text-sm text-platforma-subtle">{t(recorded && !transcribing ? "voice.recorded" : transcribing ? "voice.transcribing" : "voice.requesting")}</p>}
        <div className="flex items-center justify-between gap-3">
          <Button variant="ghost" onClick={cancelAudio}>{t("voice.discardRecording")}</Button>
          {(recorder.state === "recording" || recorded && !transcribing) && <Button
            disabled={speechError != null && (!speechIssue.retryable || speechRetryDelay > 0)}
            aria-label={t(speechError ? "common.retry" : "agentChat.send")} onClick={() => { void stop(); }}>
            <ArrowUp size={20} aria-hidden="true" />{speechRetryDelay > 0 ? t("fallback.retryAfter", { seconds: speechRetryDelay }) : t(speechError ? "common.retry" : "agentChat.send")}</Button>}
        </div>
      </> : <>
        <Button variant="secondary" className="min-h-12 flex-1 rounded-full" disabled={!status.ready || chat.busy || Boolean(unsent) || chat.history.isError}
          onClick={() => { setError(null); setSpeechError(null); void recorder.start(preferences.device); }}><Mic size={20} aria-hidden="true" />{t(text ? "voice.recordAgain" : "voice.record")}</Button>
        {(chat.selected || draft || unsent) && <Button size="icon" variant="ghost" aria-label={t("agentChat.new")} disabled={chat.busy}
          onClick={() => { recorder.cancel(); chat.newConversation(); setText(""); setDraft(false); setUnsent(null); setError(null); }}><RotateCcw size={18} aria-hidden="true" /></Button>}
      </>}
    </div>
    {!draft && !unsent && !audioBusy && (recorder.error || error || speechError || !status.ready) && <Button variant="ghost" disabled={chat.busy}
      onClick={() => { cancelAudio(); setError(null); setDraft(true); focusTranscript.current = true; requestAnimationFrame(() => textInput.current?.focus()); }}>{t("voice.typeInstead")}</Button>}
    {!audioBusy && !recorded && <Link className="platforma-focus-ring inline-flex min-h-10 items-center text-sm text-platforma-subtle underline underline-offset-4"
      to={`/app/voice/history${chat.selected ? `?conversation=${encodeURIComponent(chat.selected)}` : ""}`}>{t("voice.history")}</Link>}
  </div>;
}

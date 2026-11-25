import { useEffect, useRef, useState } from "react";
import { speechApi, type SpeechLanguage } from "../../api/speech";
import { connectSpeechStream, type SpeechStream } from "../../api/speechStream";
import type { Id } from "../../types";

export function useLiveSpeech(business: Id) {
  const [partial, setPartial] = useState("");
  const [connecting, setConnecting] = useState(false);
  const session = useRef<SpeechStream | null>(null);
  const controller = useRef<AbortController | null>(null);
  const cancel = () => {
    controller.current?.abort(); controller.current = null;
    session.current?.cancel(); session.current = null; setConnecting(false);
  };
  useEffect(() => () => { controller.current?.abort(); session.current?.cancel(); }, []);
  async function start(language: SpeechLanguage, onFailure: (error: unknown) => void) {
    cancel(); setPartial(""); setConnecting(true);
    const active = new AbortController(); controller.current = active;
    try {
      const { token } = await speechApi.session(business, active.signal);
      if (active.signal.aborted) return null;
      const stream = await connectSpeechStream({ token, language, signal: active.signal,
        onPartial: value => { if (!active.signal.aborted) setPartial(value); },
        onFailure: error => { if (!active.signal.aborted) onFailure(error); },
      });
      if (active.signal.aborted) { stream.cancel(); return null; }
      session.current = stream; return stream;
    } catch (error) { if (!active.signal.aborted) onFailure(error); return null; }
    finally { if (controller.current === active) setConnecting(false); }
  }
  return { partial, connecting, start, cancel, session };
}

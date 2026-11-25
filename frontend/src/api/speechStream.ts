export class SpeechStreamError extends Error {
  code: string;
  constructor(code: string) { super(code); this.code = code; this.name = "SpeechStreamError"; }
}

export function pcmBase64(samples: Float32Array) {
  const bytes = new Uint8Array(samples.length * 2);
  const view = new DataView(bytes.buffer);
  for (let i = 0; i < samples.length; i++) {
    const value = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(i * 2, Math.round(value * (value < 0 ? 32768 : 32767)), true);
  }
  let binary = "";
  for (const value of bytes) binary += String.fromCharCode(value);
  return btoa(binary);
}

export type SpeechStream = { send: (samples: Float32Array) => void; finish: () => Promise<string>; cancel: () => void };

export function connectSpeechStream({ token, language, signal, onPartial, onFailure }: {
  token: string; language: "auto" | "ru" | "kk"; signal: AbortSignal;
  onPartial: (text: string) => void; onFailure: (error: SpeechStreamError) => void;
}): Promise<SpeechStream> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) { reject(new SpeechStreamError("provider_unavailable")); return; }
    const query = new URLSearchParams({ token, model_id: "scribe_v3_live", audio_format: "pcm_16000",
      commit_strategy: "manual", enable_logging: "false" });
    if (language !== "auto") { query.set("language_code", language); query.append("secondary_languages", language === "kk" ? "ru" : "kk"); }
    const socket = new WebSocket(`wss://api.elevenlabs.io/v1/speech-to-text/realtime?${query}`);
    let closed = false, ready = false, finishing = false, frames = 0;
    let finalResolve: ((text: string) => void) | undefined;
    let finalReject: ((error: SpeechStreamError) => void) | undefined;
    let timer: ReturnType<typeof setTimeout>;
    const close = () => {
      closed = true; clearTimeout(timer); signal.removeEventListener("abort", cancel);
      socket.onmessage = null; socket.onerror = null; socket.onclose = null; socket.close();
    };
    const fail = (code: string) => {
      if (closed) return;
      const error = new SpeechStreamError(code);
      close(); reject(error); finalReject?.(error); if (ready) onFailure(error);
    };
    const cancel = () => {
      if (closed) return;
      const error = new SpeechStreamError("provider_unavailable");
      close(); reject(error); finalReject?.(error);
    };
    const stream: SpeechStream = {
      send(samples) {
        if (closed || !ready || finishing) return;
        frames += samples.length;
        if (frames > 16000 * 61 || socket.bufferedAmount > 256_000) { fail("provider_unavailable"); return; }
        try { socket.send(JSON.stringify({ message_type: "input_audio_chunk", audio_base_64: pcmBase64(samples), sample_rate: 16000 })); }
        catch { fail("provider_unavailable"); }
      },
      finish() {
        if (closed || !ready || finishing) return Promise.reject(new SpeechStreamError("provider_unavailable"));
        finishing = true;
        return new Promise((done, failed) => {
          finalResolve = done; finalReject = failed;
          clearTimeout(timer); timer = setTimeout(() => fail("speech_timeout"), 10000);
          // Flush the final segment without replaying any captured speech.
          try { socket.send(JSON.stringify({ message_type: "input_audio_chunk", audio_base_64: pcmBase64(new Float32Array(1600)), commit: true, sample_rate: 16000 })); }
          catch { fail("provider_unavailable"); }
        });
      },
      cancel,
    };
    signal.addEventListener("abort", cancel, { once: true });
    timer = setTimeout(() => fail("speech_timeout"), 10000);
    socket.onerror = () => fail("provider_unavailable");
    socket.onclose = () => fail("provider_unavailable");
    socket.onmessage = event => {
      if (closed) return;
      try {
        if (typeof event.data !== "string" || event.data.length > 32000) { fail("invalid_response"); return; }
        const data = JSON.parse(event.data) as Record<string, unknown>;
        const kind = data.message_type;
        if (kind === "session_started") {
          if (ready) { fail("invalid_response"); return; }
          ready = true; clearTimeout(timer); timer = setTimeout(() => fail("speech_timeout"), 70000);
          resolve(stream);
        } else if (kind === "partial_transcript" || kind === "committed_transcript") {
          if (!ready || typeof data.text !== "string" || data.text.length > 4000) { fail("invalid_response"); return; }
          if (kind === "partial_transcript") onPartial(data.text);
          else if (finishing) {
            const text = data.text.trim();
            if (!text) { fail("no_speech"); return; }
            close(); finalResolve?.(text);
          } else { fail("invalid_response"); }
        } else {
          const codes: Record<string, string> = { warning: "provider_rejected", auth_error: "provider_rejected",
            quota_exceeded: "speech_payment_required", rate_limited: "rate_limited", unaccepted_terms: "provider_rejected" };
          fail(typeof kind === "string" ? codes[kind] || "provider_unavailable" : "invalid_response");
        }
      } catch { fail("invalid_response"); }
    };
  });
}

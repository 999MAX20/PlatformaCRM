import { useCallback, useEffect, useRef, useState } from "react";
import workletUrl from "./pcm-worklet.js?url&no-inline";
import { encodeWave } from "./audio";

type Capture = {
  stream: MediaStream; context: AudioContext; source: MediaStreamAudioSourceNode; sink: GainNode;
  node: AudioWorkletNode; chunks: Float32Array[]; frames: number; meterOnly: boolean;
  watchdog?: number; finish?: (completed: boolean) => void;
};
type CaptureMessage = { type: "chunk"; samples: Float32Array; offset: number }
  | { type: "finished"; frames: number } | { type: "interrupted" };
export function useVoiceRecorder() {
  const [state, setState] = useState<"idle" | "requesting" | "recording" | "stopping">("idle");
  const [error, setError] = useState("");
  const [seconds, setSeconds] = useState(0);
  const [level, setLevel] = useState(0);
  const [waveform, setWaveform] = useState<number[]>([]);
  const capture = useRef<Capture | null>(null);
  const generation = useRef(0);
  const limitCallback = useRef<() => void>(() => {});
  const release = useCallback(() => {
    const current = capture.current; capture.current = null;
    if (current) {
      current.finish?.(false);
      window.clearInterval(current.watchdog);
      current.stream.getTracks().forEach(track => { track.onended = null; track.onmute = null; track.stop(); });
      current.context.onstatechange = null;
      current.node.port.onmessage = null; current.node.onprocessorerror = null;
      current.source.disconnect(); current.node.disconnect(); current.sink.disconnect();
      void current.context.close().catch(() => {});
    }
    return current;
  }, []);
  const cancel = useCallback(() => {
    generation.current++; release(); setState("idle"); setSeconds(0); setLevel(0); setWaveform([]); setError("");
  }, [release]);
  useEffect(() => () => { generation.current++; release(); }, [release]);
  const start = async (deviceId: string, meterOnly = false, onChunk?: (samples: Float32Array) => void) => {
    cancel(); setError(""); setState("requesting");
    const version = generation.current;
    let pendingStream: MediaStream | null = null;
    let pendingContext: AudioContext | null = null;
    try {
      if (!navigator.mediaDevices?.getUserMedia || !window.AudioContext) throw new Error("unsupported");
      const context = new AudioContext(onChunk ? { sampleRate: 16000 } : undefined);
      pendingContext = context;
      if (onChunk && context.sampleRate !== 16000) throw new Error("unsupported_sample_rate");
      await context.resume();
      await context.audioWorklet.addModule(workletUrl);
      if (generation.current !== version) { void context.close().catch(() => {}); return; }
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1,
        echoCancellation: false, noiseSuppression: false, autoGainControl: false,
        ...(deviceId ? { deviceId: { exact: deviceId } } : {}) } });
      pendingStream = stream;
      if (generation.current !== version) { stream.getTracks().forEach(track => track.stop()); void context.close().catch(() => {}); return; }
      const node = new AudioWorkletNode(context, "voice-pcm");
      const source = context.createMediaStreamSource(stream);
      const sink = context.createGain(); sink.gain.value = 0;
      const current: Capture = { stream, context, source, sink, node, chunks: [], frames: 0, meterOnly };
      capture.current = current;
      source.connect(node); node.connect(sink); sink.connect(context.destination);
      let lastUpdate = 0;
      let lastChunk = performance.now();
      let limitReached = false;
      const interrupt = () => {
        if (capture.current !== current) return;
        cancel(); setError("interrupted");
      };
      node.port.onmessage = (event: MessageEvent<CaptureMessage>) => {
        if (capture.current !== current) return;
        const data = event.data;
        if (data.type === "interrupted") { interrupt(); return; }
        if (data.type === "finished") { current.finish?.(data.frames === current.frames); return; }
        if (data.offset !== current.frames) { interrupt(); return; }
        lastChunk = performance.now();
        if (current.frames === 0 && !current.finish) setState("recording");
        current.frames += data.samples.length;
        if (!meterOnly) current.chunks.push(data.samples);
        onChunk?.(data.samples);
        const elapsed = current.frames / context.sampleRate;
        if (elapsed - lastUpdate >= 1 / 30) {
          lastUpdate = elapsed; setSeconds(Math.min(60, elapsed));
          const amplitude = Math.min(1, Math.sqrt(data.samples.reduce((sum, value) => sum + value * value, 0) / data.samples.length) * 5);
          setLevel(amplitude); setWaveform(values => [...values.slice(-83), amplitude]);
        }
        if (elapsed >= 60 && !limitReached) { limitReached = true; if (meterOnly) cancel(); else limitCallback.current(); }
      };
      node.onprocessorerror = interrupt;
      stream.getAudioTracks().forEach(track => { track.onended = interrupt; track.onmute = interrupt; });
      await context.resume();
      if (generation.current !== version) return;
      context.onstatechange = () => { if (context.state !== "running") interrupt(); };
      current.watchdog = window.setInterval(() => {
        if (!current.finish && performance.now() - lastChunk > (current.frames ? 2000 : 5000)) interrupt();
      }, 500);
      return true;
    } catch (cause) {
      pendingStream?.getTracks().forEach(track => track.stop());
      if (pendingContext && pendingContext !== capture.current?.context) void pendingContext.close().catch(() => {});
      if (generation.current !== version) return;
      release(); setState("idle");
      setError(cause instanceof DOMException && cause.name === "NotAllowedError" ? "permission" : "device");
      return false;
    }
  };
  const stop = async () => {
    const current = capture.current;
    if (!current || current.meterOnly || current.finish) return null;
    const version = ++generation.current;
    setState("stopping");
    // Port messages are ordered: the acknowledgement follows every captured chunk.
    const completed = await new Promise<boolean>(resolve => {
      const timer = window.setTimeout(() => resolve(false), 2000);
      current.finish = success => { window.clearTimeout(timer); resolve(success); };
      current.node.port.postMessage({ type: "finish" });
    });
    if (generation.current !== version || capture.current !== current) return null;
    release(); setState("idle"); setLevel(0);
    if (!completed) { setError("interrupted"); return null; }
    return encodeWave(current.chunks, current.context.sampleRate);
  };
  return { state, error, seconds, level, waveform, start, stop, cancel, limitCallback };
}

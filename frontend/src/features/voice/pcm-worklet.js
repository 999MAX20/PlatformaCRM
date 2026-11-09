class VoicePCM extends AudioWorkletProcessor {
  constructor() {
    super();
    this.finished = false;
    this.buffer = new Float32Array(1024);
    this.used = 0;
    this.frames = 0;
    this.nextFrame = null;
    this.port.onmessage = event => {
      if (event.data?.type === "finish") {
        this.flush();
        this.finished = true;
        this.port.postMessage({ type: "finished", frames: this.frames });
      }
    };
  }
  flush() {
    if (!this.used) return;
    const samples = this.buffer.slice(0, this.used);
    this.port.postMessage({ type: "chunk", samples, offset: this.frames - this.used }, [samples.buffer]);
    this.used = 0;
  }
  process(inputs) {
    if (this.finished) return true;
    const channels = inputs[0];
    if (channels?.length && channels[0].length) {
      if (this.nextFrame !== null && currentFrame !== this.nextFrame) {
        this.finished = true;
        this.port.postMessage({ type: "interrupted", reason: "timeline" });
        return true;
      }
      this.nextFrame = currentFrame + channels[0].length;
      for (let i = 0; i < channels[0].length; i++) {
        let sample = 0;
        for (const channel of channels) sample += channel[i] / channels.length;
        this.buffer[this.used++] = sample;
        this.frames++;
        if (this.used === this.buffer.length) this.flush();
      }
    } else if (this.nextFrame !== null) {
      this.finished = true;
      this.port.postMessage({ type: "interrupted", reason: "input" });
    }
    return true;
  }
}
registerProcessor("voice-pcm", VoicePCM);

export function encodeWave(chunks: Float32Array[], sampleRate: number): Blob {
  const total = Math.min(chunks.reduce((sum, chunk) => sum + chunk.length, 0), sampleRate * 60);
  const samples = new Float32Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    const size = Math.min(chunk.length, total - offset);
    if (!size) break;
    samples.set(chunk.subarray(0, size), offset); offset += size;
  }
  const count = Math.floor(total * 16000 / sampleRate);
  const bytes = new ArrayBuffer(44 + count * 2);
  const view = new DataView(bytes);
  const text = (at: number, value: string) => [...value].forEach((char, i) => view.setUint8(at + i, char.charCodeAt(0)));
  text(0, "RIFF"); view.setUint32(4, 36 + count * 2, true); text(8, "WAVE"); text(12, "fmt ");
  view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
  view.setUint32(24, 16000, true); view.setUint32(28, 32000, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true);
  text(36, "data"); view.setUint32(40, count * 2, true);
  for (let i = 0; i < count; i++) {
    const position = i * sampleRate / 16000, index = Math.floor(position), fraction = position - index;
    const value = Math.max(-1, Math.min(1, samples[index] * (1 - fraction) + (samples[index + 1] ?? samples[index]) * fraction));
    view.setInt16(44 + i * 2, Math.round(value * (value < 0 ? 32768 : 32767)), true);
  }
  return new Blob([bytes], { type: "audio/wav" });
}

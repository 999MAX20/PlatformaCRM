import { apiClient } from "./client";
import type { Id } from "../types";

export type SpeechStatus = { business: Id; ready: boolean; max_seconds: number; max_bytes: number };
export type SpeechLanguage = "auto" | "ru" | "kk";
export const speechApi = {
  async status(business: Id) {
    return (await apiClient.get<SpeechStatus>("/api/ai/speech/", { params: { business } })).data;
  },
  async transcribe(business: Id, audio: Blob, language: SpeechLanguage, signal: AbortSignal,
    currentEntity?: { entity: "clients" | "tasks" | "appointments"; id: number }) {
    const form = new FormData();
    form.append("business", String(business)); form.append("language", language);
    form.append("audio", audio, "recording.wav"); form.append("format_text", "false");
    if (currentEntity) form.append("current_entity", JSON.stringify(currentEntity));
    return (await apiClient.post<{ text: string }>("/api/ai/speech/", form,
      { signal, timeout: 65000, headers: { "Content-Type": undefined } })).data;
  },
};

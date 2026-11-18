import { useEffect, useState } from "react";
import type { Id } from "../../types";
import type { SpeechLanguage } from "../../api/speech";
import { useI18n } from "../../lib/i18n";

type Preferences = { visible: boolean; language: SpeechLanguage; device: string };
export function useVoicePreferences(userId: Id) {
  const { language } = useI18n();
  const defaults: Preferences = { visible: true, language: language === "kk" ? "kk" : language === "ru" ? "ru" : "auto", device: "" };
  const key = `voice-preferences:${userId}`;
  const read = (): Preferences => {
    try {
      const value = JSON.parse(localStorage.getItem(key) || "{}");
      return { visible: value.visible !== false, language: ["auto", "ru", "kk"].includes(value.language) ? value.language : defaults.language,
        device: typeof value.device === "string" ? value.device : "" };
    } catch { return defaults; }
  };
  const [preferences, setPreferences] = useState(read);
  useEffect(() => {
    const refresh = (event?: Event) => {
      if (event instanceof CustomEvent && event.detail?.key === key) setPreferences(event.detail.value);
      else if (!(event instanceof CustomEvent)) setPreferences(read());
    };
    refresh(); window.addEventListener("voice-preferences", refresh); window.addEventListener("storage", refresh);
    return () => { window.removeEventListener("voice-preferences", refresh); window.removeEventListener("storage", refresh); };
  }, [key, language]);
  const update = (patch: Partial<Preferences>) => {
    const next = { ...preferences, ...patch };
    try { localStorage.setItem(key, JSON.stringify(next)); } catch { /* Preferences still work for this mounted view. */ }
    setPreferences(next); window.dispatchEvent(new CustomEvent("voice-preferences", { detail: { key, value: next } }));
  };
  return { preferences, update };
}

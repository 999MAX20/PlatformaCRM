import { useEffect, useState } from "react";
import { Button } from "../../../components/ui/Button";
import { Select } from "../../../components/ui/Select";
import { SettingsSection } from "../components/SettingsLayout";
import type { SettingsModel } from "../useSettingsModel";
import { useVoicePreferences } from "../../voice/useVoicePreferences";
import { useVoiceRecorder } from "../../voice/useVoiceRecorder";
import { useAuth } from "../../auth/AuthProvider";
import { useI18n } from "../../../lib/i18n";
import type { SpeechLanguage } from "../../../api/speech";
import type { Id } from "../../../types";

export function VoiceInputSection({ model }: { model: SettingsModel }) {
  const { user } = useAuth();
  return <SettingsSection id="voice-input" active={model.activeSettingsSection} title={model.t("voice.title")}>
    {user && model.activeSettingsSection === "voice-input" && <VoiceSettings key={user.id} userId={user.id} />}
  </SettingsSection>;
}
export function VoiceSettings({ userId }: { userId: Id }) {
  const { t } = useI18n(); const { preferences, update } = useVoicePreferences(userId);
  const recorder = useVoiceRecorder(); const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  useEffect(() => {
    let alive = true;
    const refresh = () => { void navigator.mediaDevices?.enumerateDevices().then(values => { if (alive) setDevices(values.filter(value => value.kind === "audioinput")); }).catch(() => {}); };
    refresh(); navigator.mediaDevices?.addEventListener("devicechange", refresh);
    return () => { alive = false; navigator.mediaDevices?.removeEventListener("devicechange", refresh); };
  }, [recorder.state]);
  return <div className="space-y-5 p-4 sm:p-5">
    <label className="flex min-h-10 items-center gap-3 text-sm"><input type="checkbox" checked={preferences.visible} onChange={event => update({ visible: event.target.checked })} />{t("voice.visible")}</label>
    <Select label={t("voice.language")} value={preferences.language} onChange={event => update({ language: event.target.value as SpeechLanguage })}
      options={[{ value: "auto", label: t("voice.auto") }, { value: "ru", label: "Русский" }, { value: "kk", label: "Қазақша" }]} />
    <Select label={t("voice.device")} value={preferences.device} disabled={recorder.state !== "idle"} onChange={event => update({ device: event.target.value })}
      options={[{ value: "", label: t("voice.system") }, ...devices.filter(device => device.deviceId).map((device, index) => ({ value: device.deviceId, label: device.label || t("voice.numberedDevice", { number: index + 1 }) })),
        ...(preferences.device && !devices.some(device => device.deviceId === preferences.device) ? [{ value: preferences.device, label: t("voice.deviceMissing") }] : [])]} />
    <div className="flex flex-wrap items-center gap-3"><Button variant="secondary" onClick={() => recorder.state === "idle" ? void recorder.start(preferences.device, true) : recorder.cancel()}>
      {t(recorder.state === "idle" ? "voice.test" : "voice.stopTest")}</Button>
      {recorder.state === "recording" && <meter className="h-3 flex-1" min={0} max={1} value={recorder.level} aria-label={t("voice.level")} />}
      {recorder.state === "requesting" && <span role="status" className="text-sm">{t("voice.requesting")}</span>}</div>
    {recorder.error && <p role="alert" className="text-sm text-platforma-danger">{t(`voice.error.${recorder.error}`)}</p>}
  </div>;
}

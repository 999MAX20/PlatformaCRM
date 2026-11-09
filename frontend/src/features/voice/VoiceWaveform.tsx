import { useI18n } from "../../lib/i18n";

export function VoiceWaveform({ values, level, seconds }: { values: number[]; level: number; seconds: number }) {
  const { t } = useI18n();
  const bars = [...Array<number>(Math.max(0, 84 - values.length)).fill(0), ...values];
  return <div className="min-w-0 flex-1">
    <svg viewBox="0 0 336 48" className="h-12 w-full text-platforma-text" preserveAspectRatio="none" aria-hidden="true" data-testid="voice-waveform">
      {bars.map((value, index) => {
        const height = Math.max(1, Math.sqrt(value) * 40);
        return <line key={index} x1={index * 4 + 2} x2={index * 4 + 2} y1={24 - height / 2} y2={24 + height / 2}
          stroke="currentColor" strokeWidth="2" strokeLinecap="round" />;
      })}
    </svg>
    <meter className="sr-only" aria-label={t("voice.level")} min={0} max={1} value={level} />
    <output className="block text-center text-xs tabular-nums text-platforma-subtle">{Math.floor(seconds)} / 60 {t("voice.seconds")}</output>
  </div>;
}

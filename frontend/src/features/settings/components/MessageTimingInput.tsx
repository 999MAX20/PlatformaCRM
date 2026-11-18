import { useState } from "react";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import { useI18n } from "../../../lib/i18n";

export function MessageTimingInput({ minutes, after, onChange, error }: { minutes: number; after: boolean; onChange: (value: number) => void; error?: string }) {
  const { t } = useI18n();
  const [unit, setUnit] = useState(() => minutes !== 0 && minutes % 1440 === 0 ? 1440 : minutes !== 0 && minutes % 60 === 0 ? 60 : 1);
  const magnitude = Math.abs(minutes);
  // Existing values that do not divide evenly stay in minutes without rounding.
  const displayUnit = magnitude % unit === 0 ? unit : 1;
  return <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-2">
    <Input label={t(after ? "settings.clarity.after" : "settings.clarity.before")} type="number" required min={after ? 0 : 1} max={43200 / displayUnit} step={1}
      value={magnitude / displayUnit} error={error} onChange={event => onChange((after ? 1 : -1) * Number(event.target.value) * displayUnit)} />
    <Select label={t("settings.clarity.unit")} value={displayUnit} options={[1, 60, 1440].map(value => ({ value, label: t(`settings.clarity.unit.${value}`) }))}
      onChange={event => { const next = Number(event.target.value); setUnit(next); onChange((after ? 1 : -1) * (magnitude / displayUnit) * next); }} />
  </div>;
}

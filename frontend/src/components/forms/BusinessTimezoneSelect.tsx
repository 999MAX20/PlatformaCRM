import { useMemo } from "react";
import { SearchableSelect } from "../ui/SearchableSelect";
import { useI18n } from "../../lib/i18n";

const cities: Record<string, string[]> = {
  "Asia/Almaty": ["Алматы", "Алматы", "Almaty"],
  "Asia/Qyzylorda": ["Кызылорда", "Қызылорда", "Qyzylorda"],
  "Asia/Aqtobe": ["Актобе", "Ақтөбе", "Aqtobe"],
  "Asia/Aqtau": ["Актау", "Ақтау", "Aqtau"],
  "Asia/Atyrau": ["Атырау", "Атырау", "Atyrau"],
  "Asia/Oral": ["Уральск", "Орал", "Oral"],
  "Asia/Qostanay": ["Костанай", "Қостанай", "Qostanay"],
  "Europe/Moscow": ["Москва", "Мәскеу", "Moscow"],
  "Asia/Tashkent": ["Ташкент", "Ташкент", "Tashkent"],
  "Asia/Bishkek": ["Бишкек", "Бішкек", "Bishkek"],
};

export function BusinessTimezoneSelect({ value, onChange, error, disabled }: { value: string; onChange: (value: string) => void; error?: string; disabled?: boolean }) {
  const { t, language } = useI18n();
  const options = useMemo(() => {
    const supported = (Intl as typeof Intl & { supportedValuesOf?: (key: "timeZone") => string[] }).supportedValuesOf?.("timeZone") || [];
    const zones = Array.from(new Set([...Object.keys(cities), "UTC", ...supported, value].filter(Boolean)));
    return zones.map(zone => {
      const names = cities[zone];
      const city = names?.[language === "ru" ? 0 : language === "kk" ? 1 : 2] || zone.split("/").slice(1).join(" / ").replace(/_/g, " ") || zone;
      return { value: zone, label: city, description: zone, searchText: names?.join(" ") };
    });
  }, [language, value]);
  return <SearchableSelect label={t("businessForm.timezone")} value={value} options={options} onChange={onChange} error={error} disabled={disabled} />;
}

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { platformApi } from "../../api/platform";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";
import { useI18n } from "../../lib/i18n";
import { SupportError } from "./SupportUI";

export function SupportClinicPicker({ value, onChange, disabled = false, required = false }: {
  value?: number; onChange: (value: number | undefined) => void; disabled?: boolean; required?: boolean;
}) {
  const { t } = useI18n();
  const [search, setSearch] = useState("");
  const needle = useDebouncedValue(search, 250);
  const clinics = useQuery({ queryKey: ["support-clinic-picker", needle], queryFn: () => platformApi.merchants({ search: needle, page_size: 20 }) });
  const selected = useQuery({ queryKey: ["platform-merchant", String(value)], queryFn: () => platformApi.merchant(value!), enabled: Boolean(value) });
  const options = (clinics.data?.results || []).map(clinic => ({ value: String(clinic.id), label: clinic.name }));
  if (value && !options.some(option => option.value === String(value))) options.unshift({ value: String(value), label: selected.data?.name || `#${value}` });
  return <div className="min-w-0 space-y-2">
    <Input label={t("supportCases.clinicSearch")} value={search} onChange={event => setSearch(event.target.value)} disabled={disabled} />
    <Select label={t("supportCases.clinic")} value={value ? String(value) : ""} onChange={event => onChange(Number(event.target.value) || undefined)} disabled={disabled} required={required}
      options={[{ value: "", label: t(required ? "supportCases.chooseClinic" : "supportCases.allClinics") }, ...options]} />
    {clinics.isError && <SupportError error={clinics.error} retry={() => clinics.refetch()} />}
    {selected.isError && <SupportError error={selected.error} retry={() => selected.refetch()} />}
  </div>;
}

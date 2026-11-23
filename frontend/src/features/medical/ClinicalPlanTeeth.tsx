import { useLayoutEffect, useRef } from "react";
import { Button } from "../../components/ui/Button";
import { Select } from "../../components/ui/Select";
import { useI18n } from "../../lib/i18n";

const numbers = Array.from({ length: 8 }, (_, q) => Array.from({ length: q < 4 ? 8 : 5 }, (_, n) => (q + 1) * 10 + n + 1)).flat();

export function ClinicalPlanTeeth({ value = [], onChange, disabled, readOnly }: {
  value?: number[]; onChange: (value: number[]) => void; disabled: boolean; readOnly: boolean;
}) {
  const { t } = useI18n();
  const root = useRef<HTMLDivElement>(null);
  const returnFocus = useRef(false);
  useLayoutEffect(() => {
    if (returnFocus.current) {
      root.current?.querySelector<HTMLButtonElement>('[aria-haspopup="listbox"]')?.focus();
      returnFocus.current = false;
    }
  }, [value]);
  if (readOnly) return value.length ? <p className="break-words text-sm">{t("medical.plan.teeth")}: {value.join(", ")}</p> : null;
  return <div ref={root} className="space-y-2" data-testid="clinical-plan-teeth">
    <Select portal label={t("medical.plan.teeth")} value="" disabled={disabled || value.length === numbers.length}
      onChange={event => { const tooth = Number(event.target.value); if (numbers.includes(tooth) && !value.includes(tooth)) onChange([...value, tooth]); }}
      options={[{ value: "", label: t("medical.plan.addTooth") }, ...numbers.filter(tooth => !value.includes(tooth))
        .map(tooth => ({ value: tooth, label: `${t("medical.tooth.tooth")} ${tooth}` }))]} />
    {value.length ? <div className="flex flex-wrap gap-2">{value.map(tooth => <Button key={tooth} type="button" size="lg"
      variant="secondary" disabled={disabled} aria-label={t("medical.plan.removeTooth", { tooth })} onClick={() => {
        returnFocus.current = true;
        onChange(value.filter(item => item !== tooth));
      }}>{tooth} ×</Button>)}</div> : null}
  </div>;
}

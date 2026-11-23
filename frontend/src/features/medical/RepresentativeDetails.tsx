import type { Representative } from "../../api/medicalRepresentatives";
import { useI18n } from "../../lib/i18n";

export function RepresentativeDetails({ row }: { row: Representative }) {
  const { t, language } = useI18n();
  const date = (value: string) => new Intl.DateTimeFormat(language, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
  return <>
    <div className="flex flex-wrap items-center justify-between gap-2"><span className="break-words font-semibold text-platforma-text">{row.full_name}</span>
      <span className="text-platforma-subtle">{t(`medical.repStatus.${row.status}`)}</span></div>
    <p className="break-words text-platforma-text">{row.permission_labels ? row.permissions.map(code => row.permission_labels![code][language]).join(", ") : t("medical.repLabelsUnavailable")}</p>
    <dl className="grid grid-cols-1 gap-2 sm:grid-cols-2">
      <div><dt className="text-platforma-subtle">{t("medical.repFrom")}</dt><dd>{date(row.valid_from)}</dd></div>
      <div><dt className="text-platforma-subtle">{t("medical.repUntil")}</dt><dd>{row.valid_until ? date(row.valid_until) : t("medical.repNoExpiry")}</dd></div>
    </dl>
  </>;
}

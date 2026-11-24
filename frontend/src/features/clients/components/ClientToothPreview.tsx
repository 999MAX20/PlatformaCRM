import type { ToothObservation } from "../../../api/medicalTooth";
import { useI18n } from "../../../lib/i18n";

// Compact crown view; the full medical chart owns editing and the status legend.
export function ClientToothPreview({ observations }: { observations: ToothObservation[] }) {
  const { t } = useI18n();
  const rows = [
    [18,17,16,15,14,13,12,11,21,22,23,24,25,26,27,28],
    [48,47,46,45,44,43,42,41,31,32,33,34,35,36,37,38],
  ];
  const primary = observations.some(item => item.tooth >= 51);
  if (primary) rows.push([55,54,53,52,51,61,62,63,64,65], [85,84,83,82,81,71,72,73,74,75]);
  const colors: Record<string, string> = { caries: "#ef737b", filling: "#6a9ee8", crown: "#c0a04b", implant: "#8794a6", observation: "#e7b65b", no_findings: "#d5e8df" };
  return <svg viewBox={`0 0 260 ${primary ? 240 : 126}`} role="img" aria-label={t("medical.tooth.title")}>
    {rows.map((row, rowIndex) => row.map((tooth, index) => {
      const state = observations.filter(item => item.tooth === tooth).sort((a,b) => Date.parse(b.observed_at) - Date.parse(a.observed_at) || b.history_id - a.history_id)[0];
      const status = state?.tooth_status || "not_examined";
      const offset = (index - (row.length - 1) / 2) / ((row.length - 1) / 2);
      const lower = rowIndex % 2 === 1;
      const x = 20 + index * 220 / (row.length - 1);
      const y = Math.floor(rowIndex / 2) * 120 + (lower ? 98 - 24 * offset ** 2 : 24 + 24 * offset ** 2);
      return <g key={tooth} transform={`translate(${x} ${y}) rotate(${offset * (lower ? 35 : -35)})`}>
        <title>{`${tooth}: ${t(`medical.tooth.status.${status}`)}`}</title>
        <path d="M-6 -10 Q0 -13 6 -10 Q9 -5 7 7 Q0 12 -7 7 Q-9 -5 -6 -10Z" fill={colors[status] || "white"} stroke="#81928c" strokeWidth="0.7" strokeDasharray={status === "absent" ? "2 2" : undefined} opacity={status === "absent" ? 0.4 : 1} />
        {status === "absent" && <path d="M-5 -6 L5 6 M5 -6 L-5 6" stroke="#81928c" strokeWidth="0.8" />}
      </g>;
    }))}
  </svg>;
}

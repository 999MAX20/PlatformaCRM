import { formatDateTime } from "../../../lib/format";
import { useI18n } from "../../../lib/i18n";
import { useActiveBusiness } from "../../../hooks/useBusiness";
import type { useCustomColumns } from "../../../components/crm/CustomFieldColumns";
import type { ClientTableRow, Translate } from "../types";
import { ClientStatusBadge } from "./ClientPrimitives";

export function MobileClientCards({ rows, onOpenClient, customColumns, t }: {
  rows: ClientTableRow[];
  onOpenClient: (id: number) => void;
  customColumns: ReturnType<typeof useCustomColumns>["columns"];
  t: Translate;
}) {
  const { language } = useI18n();
  const { business } = useActiveBusiness();
  return <ul className="divide-y divide-platforma-border md:hidden">{rows.map(row => <li key={row.client.id} className="p-4">
    <button type="button" data-testid="client-card-action-open" onClick={() => onOpenClient(row.client.id)} className="platforma-focus-ring block w-full space-y-2 rounded text-left">
      <span className="flex items-start justify-between gap-3"><span className="min-w-0 break-words font-medium text-brand-700">{row.client.full_name}</span><ClientStatusBadge status={row.status} t={t} /></span>
      <span className="block break-all text-xs text-platforma-subtle">{row.client.phone || row.client.email || t("clients.noContacts")}</span>
      {row.lastContactAt && <span className="block text-xs text-platforma-subtle">{t("clients.lastActivity")}: {formatDateTime(row.lastContactAt, business?.timezone || "Asia/Qyzylorda", true, language)}</span>}
      {row.nextStep.title && <span className="block text-sm">{row.nextStep.title}</span>}
      {customColumns.map(column => <span key={column.id} className="block break-words text-sm"><span className="text-platforma-subtle">{column.header}: </span>{column.cell(row.client)}</span>)}
    </button>
    {row.client.phone && <a href={`tel:${row.client.phone}`} className="platforma-focus-ring mt-2 inline-flex min-h-11 items-center rounded px-2 text-sm text-brand-700 underline-offset-4 hover:underline">{t("clients.call")}</a>}
  </li>)}</ul>;
}

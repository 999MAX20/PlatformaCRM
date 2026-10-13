import { Columns3 } from "lucide-react";
import { Button } from "../../../components/ui/Button";
import { CrmFilterControls } from "../../../components/crm/CrmFilterControls";
import { CrmWorkspacePopover } from "../../../components/crm/CrmWorkspacePopover";
import type { ClientTableColumn, Translate } from "../types";
export function ClientsFilters({ tagOptions, segmentOptions, sourceOptions, counts, visibleColumns, onToggleColumn, onOpenSegment, t }: {
  tagOptions: Array<{ value: string | number; label: string }>;
  segmentOptions: Array<{ value: string | number; label: string }>;
  sourceOptions: Array<{ value: string | number; label: string }>;
  counts?: Record<string, number | undefined>;
  visibleColumns: Set<ClientTableColumn>;
  onToggleColumn: (column: ClientTableColumn) => void;
  onOpenSegment: () => void;
  t: Translate;
}) {
  return <CrmFilterControls kind="clients" searchLabel={t("clients.search")} counts={counts}
    options={{ source: sourceOptions, tag: tagOptions, segment: segmentOptions }}
    extraFilterAction={<Button type="button" variant="secondary" size="sm" onClick={onOpenSegment}>{t("clients.segment")}</Button>}
    actions={<CrmWorkspacePopover label={t("clients.columns")} icon={<Columns3 size={16} />}>
      {(["source", "manager"] as const).map(column => <label key={column} className="flex min-h-11 items-center gap-3 rounded-control px-2 text-sm hover:bg-surface-hover"><input type="checkbox" checked={visibleColumns.has(column)} onChange={() => onToggleColumn(column)} />{t(`clients.${column}`)}</label>)}
    </CrmWorkspacePopover>} />;
}

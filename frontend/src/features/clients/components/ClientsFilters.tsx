import { Columns3 } from "lucide-react";
import { CrmFilterControls } from "../../../components/crm/CrmFilterControls";
import { CrmWorkspacePopover } from "../../../components/crm/CrmWorkspacePopover";
import type { useCustomColumns } from "../../../components/crm/CustomFieldColumns";
import type { ClientTableColumn, Translate } from "../types";

export function ClientsFilters({ tagOptions, sourceOptions, counts, visibleColumns, onToggleColumn, customTable, t }: {
  tagOptions: Array<{ value: string | number; label: string }>;
  sourceOptions: Array<{ value: string | number; label: string }>;
  counts?: Record<string, number | undefined>;
  visibleColumns: Set<ClientTableColumn>;
  onToggleColumn: (column: ClientTableColumn) => void;
  customTable: ReturnType<typeof useCustomColumns>;
  t: Translate;
}) {
  return <CrmFilterControls kind="clients" compact searchLabel={t("clients.search")} counts={counts}
    options={{ source: sourceOptions, tag: tagOptions }} customDefinitions={customTable.definitions}
    actions={<>
      <CrmWorkspacePopover label={t("clients.columns")} icon={<Columns3 size={16} />}>
        {(["source", "manager"] as const).map(column => <label key={column} className="flex min-h-11 items-center gap-3 rounded-control px-2 text-sm hover:bg-surface-hover"><input type="checkbox" checked={visibleColumns.has(column)} onChange={() => onToggleColumn(column)} />{t(`clients.${column}`)}</label>)}
        {customTable.columnControls && <div className="mt-2 border-t border-platforma-border pt-2">{customTable.columnControls}</div>}
      </CrmWorkspacePopover>
    </>} />;
}
